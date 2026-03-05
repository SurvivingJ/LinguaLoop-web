import logging
import os
from flask import Flask
from flask_cors import CORS
from config import Config
from models.csv_store import CSVStore

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.url_map.strict_slashes = False

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize CSV store
    app.store = CSVStore(app.config['DATA_STORE_DIR'])

    # Auto-seed if no data exists yet (Railway has ephemeral storage)
    _auto_seed_if_needed(app)

    # Register blueprints
    _register_blueprints(app)

    # Initialize scheduler (skip during testing)
    if not app.config.get('TESTING'):
        _init_scheduler(app)

    return app


def _auto_seed_if_needed(app):
    """Seed products, settings, and recipes if CSV store is empty."""
    recipes_path = os.path.join(app.config['DATA_STORE_DIR'], 'recipes.csv')
    if not os.path.exists(recipes_path):
        try:
            app.logger.info("No recipes.csv found — running auto-seed...")
            from scripts.seed_data import seed
            seed(app.config['DATA_STORE_DIR'])
            app.logger.info("Auto-seed complete")
        except Exception as e:
            app.logger.warning(f"Auto-seed failed: {e}")


def _register_blueprints(app):
    from routes.dashboard import dashboard_bp
    from routes.planner import planner_bp
    from routes.recipes import recipes_bp
    from routes.skills import skills_bp
    from routes.wishlist import wishlist_bp
    from routes.settings import settings_bp
    from routes.api import api_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(planner_bp, url_prefix='/planner')
    app.register_blueprint(recipes_bp, url_prefix='/recipes')
    app.register_blueprint(skills_bp, url_prefix='/skills')
    app.register_blueprint(wishlist_bp, url_prefix='/wishlist')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(api_bp, url_prefix='/api')


def _init_scheduler(app):
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from jobs.daily_scrape import run_daily_scrape
        from jobs.wishlist_check import run_wishlist_check
        from jobs.offer_expiry import run_offer_cleanup

        scheduler = BackgroundScheduler(timezone='Australia/Sydney')
        scheduler.add_job(run_daily_scrape, 'cron', hour=3, minute=0, args=[app])
        scheduler.add_job(run_wishlist_check, 'cron', hour=3, minute=30, args=[app])
        scheduler.add_job(run_offer_cleanup, 'cron', hour=4, minute=0, args=[app])
        scheduler.start()
        app.scheduler = scheduler
        app.logger.info("Scheduler started with 3 daily jobs")
    except Exception as e:
        app.logger.warning(f"Failed to start scheduler: {e}")
