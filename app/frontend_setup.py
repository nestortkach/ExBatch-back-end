from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
import sys

def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


def setup_static_files(app: FastAPI) -> None:
    """Mount static files if they exist"""
    frontend_path = get_resource_path("frontend")
    assets_path = get_resource_path(os.path.join("frontend", "assets"))
    
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
        print(f"✓ Mounted assets from: {assets_path}")
    
    if os.path.exists(frontend_path):
        app.mount("/static", StaticFiles(directory=frontend_path), name="frontend")
        print(f"✓ Mounted frontend from: {frontend_path}")