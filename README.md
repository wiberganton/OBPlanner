# OBPlanner 
A python package for preperation of Open Beam Files used in Freemelt 3D printers
Install by 

pip install OBPlanner

For example see examples -> example2.py

## Streamlit build runner

Install the project requirements, then start the simple GUI with:

```powershell
streamlit run streamlit_app.py
```

The app can upload STL files, create simple cube/cylinder/sphere geometries, preview them in 3D, edit common layer strategy settings in a table, edit or load the raw build JSON file, slice the model, and run `prepare_build`.
