"""The ``tests`` blueprint; the route modules of this package register on it."""

from flask import Blueprint

tests_bp = Blueprint("tests", "routes.tests")
