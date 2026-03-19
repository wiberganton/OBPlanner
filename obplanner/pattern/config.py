"""
Pattern Configuration Module

Central configuration file for all pattern generation and compensation parameters.
Users can modify these values to control the behavior of the pattern system.

All modules (compensator.py, generator.py, functions.py) read from this configuration.
"""


# =============================================================================
# PATTERN GENERATION PARAMETERS
# =============================================================================

class PatternConfig:
    """Pattern generation settings."""
    
    # Default spacing between points (mm)
    DEFAULT_SPACING = 0.5
    
    # Pattern padding around contour (mm)
    DEFAULT_PADDING = 2.0
    
    # Laser spot radius (mm) - used for interference detection
    SPOT_RADIUS = 0.05  # 50 micrometers typical laser spot radius
    
    # Pattern types
    PATTERN_TYPE_SPOT = "spot"
    PATTERN_TYPE_LINE = "line"
    PATTERN_TYPE_HATCH = "hatch"


# =============================================================================
# COMPENSATION PARAMETERS
# =============================================================================

class CompensationConfig:
    """Energy compensation settings."""
    
    # -------------------------------------------------------------------------
    # Compensation Modes
    # -------------------------------------------------------------------------
    MODE_NONE = "none"          # No compensation applied
    MODE_EDGE = "edge"          # Edge distance compensation only
    MODE_OVERHANG = "overhang"  # Overhang compensation only
    MODE_COMBINED = "combined"  # Both edge and overhang compensation
    
    # Default compensation mode
    DEFAULT_MODE = MODE_EDGE
    
    # -------------------------------------------------------------------------
    # Edge Distance Compensation
    # -------------------------------------------------------------------------
    
    # Minimum energy at the boundary (0.0 to 1.0)
    # Lower values = stronger compensation near edges
    EDGE_ENERGY = 0.5
    
    # Distance over which edge compensation is applied (mm)
    # Points beyond this distance from edge get full energy (1.0)
    COMPENSATION_WIDTH = 2.0
    
    # -------------------------------------------------------------------------
    # Overhang Compensation
    # -------------------------------------------------------------------------
    
    # Number of lower layers to check for overhang detection
    N_LAYERS = 3
    
    # Maximum energy reduction for overhang areas (0.0 to 1.0)
    # Higher values = stronger overhang compensation
    MAX_COMPENSATION = 0.3
    
    # Minimum overhang area to trigger compensation (mm²)
    # Smaller areas are ignored
    AREA_THRESHOLD = 1.0
    
    # -------------------------------------------------------------------------
    # Precision Enhancement (Auto-Detection)
    # -------------------------------------------------------------------------
    
    # Buffer multiplier for contour auto-detection
    # buffer_distance = spacing * BUFFER_MULTIPLIER
    BUFFER_MULTIPLIER = 1.0
    
    # Resolution for buffer smoothing (higher = smoother)
    BUFFER_RESOLUTION = 64
    
    # Fallback buffer distance when spacing cannot be estimated (mm)
    FALLBACK_BUFFER = 0.5


# =============================================================================
# VISUALIZATION PARAMETERS
# =============================================================================

class VisualizationConfig:
    """Visualization and plotting settings."""
    
    # Colormap for energy visualization
    COLORMAP = 'viridis'
    
    # Energy thresholds for color-coded tooltips
    HIGH_ENERGY_THRESHOLD = 0.9   # Yellow background
    MEDIUM_ENERGY_THRESHOLD = 0.7  # Teal background
    # Below medium = Purple background
    
    # Point sizes
    POINT_SIZE = 50
    POINT_ALPHA = 0.8
    
    # Energy value display precision (decimal places)
    ENERGY_PRECISION = 6


# =============================================================================
# TESTING PARAMETERS
# =============================================================================

class TestConfig:
    """Configuration for test suite."""
    
    # Default test pattern parameters
    TEST_RADIUS = 5.0
    TEST_SPACING = 0.5
    TEST_COMPENSATION_MODE = CompensationConfig.MODE_EDGE
    
    # Accuracy thresholds
    INSIDE_ACCURACY_THRESHOLD = 98.0   # % (must be very high)
    EDGE_ACCURACY_THRESHOLD = 95.0     # %
    OVERALL_ACCURACY_THRESHOLD = 85.0  # % (can be lower for sparse patterns)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_compensation_settings(mode=None):
    """
    Get compensation settings as a dictionary.
    
    Args:
        mode: Compensation mode override (optional)
    
    Returns:
        dict: Compensation settings dictionary
    """
    return {
        'mode': mode or CompensationConfig.DEFAULT_MODE,
        'edge_energy': CompensationConfig.EDGE_ENERGY,
        'compensation_width': CompensationConfig.COMPENSATION_WIDTH,
        'n_layers': CompensationConfig.N_LAYERS,
        'max_compensation': CompensationConfig.MAX_COMPENSATION,
        'area_threshold': CompensationConfig.AREA_THRESHOLD,
    }


def get_pattern_settings(spacing=None, padding=None):
    """
    Get pattern generation settings as a dictionary.
    
    Args:
        spacing: Pattern spacing override (optional)
        padding: Pattern padding override (optional)
    
    Returns:
        dict: Pattern generation settings dictionary
    """
    return {
        'spacing': spacing or PatternConfig.DEFAULT_SPACING,
        'padding': padding or PatternConfig.DEFAULT_PADDING,
    }


# =============================================================================
# USER GUIDE
# =============================================================================

"""
HOW TO USE THIS CONFIGURATION FILE:
====================================

1. MODIFY COMPENSATION BEHAVIOR:
   - Change CompensationConfig.EDGE_ENERGY (0.0-1.0) to adjust edge compensation strength
   - Change CompensationConfig.COMPENSATION_WIDTH (mm) to adjust compensation zone size
   - Change CompensationConfig.DEFAULT_MODE to set default compensation strategy

2. MODIFY PATTERN GENERATION:
   - Change PatternConfig.DEFAULT_SPACING (mm) to control point density
   - Change PatternConfig.DEFAULT_PADDING (mm) to adjust boundary padding

3. MODIFY TEST PARAMETERS:
   - Change TestConfig.TEST_SPACING to control test pattern density
   - Change TestConfig.TEST_COMPENSATION_MODE to test different strategies

4. ADVANCED SETTINGS:
   - CompensationConfig.BUFFER_MULTIPLIER: Fine-tune auto-detection precision
   - CompensationConfig.BUFFER_RESOLUTION: Adjust contour smoothness

EXAMPLES:
=========

Stronger edge compensation (more energy reduction near edges):
    CompensationConfig.EDGE_ENERGY = 0.3  # was 0.5

Wider compensation zone:
    CompensationConfig.COMPENSATION_WIDTH = 3.0  # was 2.0

Denser pattern (more points):
    PatternConfig.DEFAULT_SPACING = 0.3  # was 0.5

Sparser pattern (fewer points):
    PatternConfig.DEFAULT_SPACING = 1.0  # was 0.5
"""
