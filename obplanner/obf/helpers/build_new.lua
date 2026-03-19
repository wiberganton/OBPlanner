-- api objects: machine, mqtt, nir_camera, obf, system

function wait(predicate, timeout, settings)
	local interval = 1
	if settings ~= nil and settings.interval ~= nil then
		interval = settings.interval
	end
	local deadline = os.time() + timeout
	while not predicate() do
		system.sleep(interval)
		if os.time() >= deadline then
			return false
		end
	end
	return true
end

function wait_for_beam_power_low()
	if
		not wait(function()
			local hv_current = machine.get_hv_current()
			return hv_current ~= nil and hv_current <= 1.0
		end, 30)
	then
		machine.clear_exposure_queue()
		error("Build Aborted: BeamPowerLow condition timed out")
	end
end

function should_do_heat_balance(heat_balance)
	return heat_balance.repetitions ~= nil and heat_balance.repetitions > 0
end

function log(message)
	system.print(message)
	mqtt.publish_field("BuildStatus", "Trace", "Activity", "current_activity", message)
end

function logfatal(message)
	message = string.format("Build Error: %s", message)
	log(message)
	machine.clear_exposure_queue()
	error(message)
end

function run_heat_balance_until_target(activeHeatBalance, layer_index, layerfeed)
	if activeHeatBalance == nil or #activeHeatBalance == 0 then
		log("No heat balance patterns for layer " .. layer_index)
		return
	end

	-- You can make this fixed, or read it from MQTT / build_info
	local post_heat_timeout = 60
	local max_heat_cycles = 100

	-- Optional: allow override from MQTT if you want
	-- local timeout_from_mqtt = mqtt.get_field(heat_balance_input, "seconds")
	-- if timeout_from_mqtt ~= nil and timeout_from_mqtt > 0 then
	-- 	post_heat_timeout = timeout_from_mqtt
	-- end

	local deadline = os.time() + post_heat_timeout
	local cycle = 0

	log(string.format(
		"Starting post-heat for layer %d until sensor '%s' reaches %.2f",
		layer_index,
		tostring(temperature_sensor),
		target_temperature
	))

	while true do
		local temperature = machine.get_temperature(temperature_sensor)

		if temperature ~= nil and temperature >= target_temperature then
			log(string.format(
				"Post-heat complete for layer %d. Temperature %.2f reached target %.2f",
				layer_index,
				temperature,
				target_temperature
			))
			return
		end

		if os.time() >= deadline then
			logfatal(string.format(
				"Post-heat timeout on layer %d. Failed to reach target temperature %.2f",
				layer_index,
				target_temperature
			))
		end

		cycle = cycle + 1
		if cycle > max_heat_cycles then
			logfatal(string.format(
				"Post-heat exceeded max cycles on layer %d",
				layer_index
			))
		end

		if not machine.beam_is_on() then
			log("Beam was off before post-heat. Turning it on.")
			if not machine.restartHV(60) then
				logfatal("Failed to restart beam before post-heat")
			end
		end

		log(string.format(
			"Post-heat cycle %d on layer %d. Current temperature: %s",
			cycle,
			layer_index,
			tostring(temperature)
		))

		-- Build one single heat-balance pass
		-- local heatBalancePatterns = {}
		for _, obp in ipairs(activeHeatBalance) do
			table.insert(heatBalancePatterns, {
				file = obp.file,
				repetitions = 1
			})
		end

		local err_id = machine.start_process_step_exposures(
			{}, -- jumpSafe
			{}, -- spatterSafe
			{}, -- melt
			{}
		)

		if err_id ~= 0 then
			local newPowderLayer = false
			machine.clear_exposure_queue()

			if err_id == 4 then
				log("Arc trip during post-heat exposure")
			else
				log("Unexpected error during post-heat, err_id = " .. tostring(err_id))
			end

			if not machine.restart_after_arc_trip(newPowderLayer, 60, layerfeed) then
				logfatal("Unable to recover from post-heat arc trip")
			end
		end
	end
end

local build_info = obf.get_build_info()
local start_heat = build_info.startHeat
local temperature_sensor = start_heat.temperatureSensor
local target_temperature = start_heat.targetTemperature

local spatterSafeDefault = build_info.layerDefaults["spatterSafe"] or {}
local jumpSafeDefault = build_info.layerDefaults["jumpSafe"] or {}
local heatBalanceDefault = build_info.layerDefaults["heatBalance"] or {}
local num_layers = #build_info.layers
local layerfeed = build_info.layerDefaults["layerFeed"] or {}

local jump_safe_input = mqtt.construct_topic("Parameters", "Name", "PreHeatRepetitions")

local maxRetryCount = 10

mqtt.publish("BuildStatus", "Trace", "Layers", {
	build_layers = num_layers,
	current_layer = 0,
})

mqtt.add_subscription(jump_safe_input)
-- mqtt.add_subscription(heat_balance_input)

local jumpreps = (jumpSafeDefault and jumpSafeDefault[1] and jumpSafeDefault[1].repetitions) or 10
local balancepreps = (heatBalanceDefault and heatBalanceDefault[1] and heatBalanceDefault[1].repetitions) or 10
mqtt.publish_field("Parameters", "Name", "PreHeatRepetitions", "repetitions", jumpreps)
--mqtt.publish_field("Parameters", "Name", "PostHeatRepetitions", "repetitions", balancepreps)

-- ========== START HEAT ==========
log("Init")
log("Turning on the beam")
if not machine.beam_is_on() and not machine.restartHV(60) then
	logfatal("Failed to start beam")
end
log("The beam is active")
log("Start heating to target temperature: " .. target_temperature)
machine.start_exposure(start_heat.file, 4294967295)
system.print("Waiting for " .. start_heat.timeout .. " seconds or until target temperature is reached.")
if
	not wait(function()
		if not machine.beam_is_on() and not machine.restartHV(60) then
			logfatal("Failed to start beam")
		end
		local temperature = machine.get_temperature(temperature_sensor)
		return temperature and temperature >= target_temperature
	end, start_heat.timeout, { interval = 0.5 })
then
	logfatal("Failed to reach target temperature")
end
if not machine.clear_exposure_queue() then
	logfatal("Failed to clear exposure queue")
end
-- ========== END START HEAT ==========

system.print("OBF has " .. num_layers .. " layers.")
for index, layer in ipairs(build_info.layers) do
	system.print("Starting to process layer " .. index)
	mqtt.publish("BuildStatus", "Trace", "Layers", {
		build_layers = num_layers,
		current_layer = index,
	})
	log("Waiting for beam power low")
	wait_for_beam_power_low()

	-- ========== RECOATE CYCLE ==========
	log("Recoat cycle. Layer " .. index .. "")
	if not machine.recoat_cycle(layerfeed) then
		logfatal("Unable to complete Layerfeed.")
	end
	-- (proheat should be in heating position)
	if not machine.beam_is_on() then
		log("Beam was off after recoating. Turning it on!")
		if not machine.restartHV(60) then
			logfatal("Timeout waiting for beam on")
		end
	end

	-- ========== EXPOSE LAYER'S OBP FILES ==========
	local layerDone = false
	local retryCount = 0
	while not layerDone do
		-- There are four process steps:
		local jumpSafePatterns = {}
		local spatterSafePatterns = {}
		local meltPatterns = {}
		local heatBalancePatterns = {}

		-- JUMP SAFE
		-- Uses the mqtt value of currentJumpSafeReps as an absolute value,
		-- meaning that it replaces the original value.

		local currentJumpSafeReps = mqtt.get_field(jump_safe_input, "repetitions")

		system.print("Jump safe reps to add: " .. currentJumpSafeReps .. "")
		
		local activeJumpSafe = layer.jumpSafe or jumpSafeDefault

		for _, obp in ipairs(activeJumpSafe) do
    			system.print("Jump Safe reps: " .. currentJumpSafeReps .. "")
    			table.insert(
        			jumpSafePatterns,
        			{ file = obp.file, repetitions = math.max(0, currentJumpSafeReps) }
    			)
		end

		-- SPATTER SAFE
		local activeSpatterSafe = layer.spatterSafe or spatterSafeDefault

		for _, obp in ipairs(activeSpatterSafe) do
    			table.insert(
        			spatterSafePatterns,
        			{ file = obp.file, repetitions = math.max(0, obp.repetitions) }
    			)
		end


		-- MELT
		if layer.melt ~= nil then
			for _, obp in ipairs(layer.melt) do
				table.insert(meltPatterns, { file = obp.file, repetitions = obp.repetitions })
			end
		end

		-- HEAT BALANCE
		-- Loops heatBalance until target temperature is reached, so we just do 1 repetition per loop and check temperature in between
		local heatBalanceRepetitions = mqtt.get_field(heat_balance_input, "repetitions")
		system.print("Heat balance reps to add: " .. heatBalanceRepetitions .. "")
		
		local activeHeatBalance = layer.heatBalance or heatBalanceDefault

		for _, obp in ipairs(activeHeatBalance) do
    			system.print("Heat Balance reps: " .. heatBalanceRepetitions .. "")
    			table.insert(
        			heatBalancePatterns,
        			{ file = obp.file, repetitions = math.max(0, heatBalanceRepetitions) }
    			)
		end

		-- EXPOSURE
		log(string.format("Exposing OBP files of layer %d.%s", index, retryCount > 0 and " Retry " .. retryCount or ""))
		local err_id = machine.start_process_step_exposures(
			jumpSafePatterns,
			spatterSafePatterns,
			meltPatterns,
			heatBalancePatterns
		)
		if err_id == 0 then
			local activeHeatBalance = layer.heatBalance or heatBalanceDefault
			run_heat_balance_until_target(activeHeatBalance, index, layerfeed)
			layerDone = true
		elseif err_id == 1 then
			log("Arc trip during Jump Safe exposure")
			layerDone = false
			newPowderLayer = false
		elseif err_id == 2 then
			log("Arc trip during Spatter Safe exposure")
			layerDone = false
			newPowderLayer = false
		elseif err_id == 3 then
			log("Arc trip during Melt exposure")
			layerDone = false
			newPowderLayer = true
		elseif err_id == 4 then
			log("Arc trip during Heat Balance exposure")
			layerDone = true
			newPowderLayer = false
		end
		if err_id ~= 0 then
			machine.clear_exposure_queue()
			if not machine.restart_after_arc_trip(newPowderLayer, 60, layerfeed) then
				logfatal("Unable to recover from arc trip")
			end
		end
		if not layerDone then
			retryCount = retryCount + 1
		end
		if retryCount > maxRetryCount then
			logfatal("Maximum retry count exceeded!")
		end
	end -- this layer done loop
end -- all layers loop

-- ========== TEARDOWN ==========

machine.clear_exposure_queue()
log("Waiting for beam power low")
wait_for_beam_power_low()
log("Turning off the beam")
machine.beam_off()
log("Turning off the PSU")
machine.power_off()
log("Build finished")
