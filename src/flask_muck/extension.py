import json
from typing import Optional

from apispec import APISpec
from flasgger import Swagger  # type: ignore
from flask import Flask, current_app

from flask_muck import FlaskMuckApiView
from flask_muck.commands import muck_cli
from flask_muck.types import JsonDict
from flask_muck.utils import register_muck_view


class FlaskMuck:
    registered_views: list[type[FlaskMuckApiView]]
    url_prefix: str
    swagger: Optional[Swagger]
    _spec: APISpec

    def __init__(self, app: Optional[Flask] = None):
        self.swagger = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        self.registered_views = []
        app.extensions["muck"] = self
        api_title = app.config.setdefault("MUCK_API_TITLE", "REST API")
        openapi_version = "3.0.3"

        self._spec = APISpec(
            title=api_title,
            version=app.config.setdefault("MUCK_API_VERSION", "1.0.0"),
            openapi_version=openapi_version,
        )
        self.url_prefix = app.config.setdefault("MUCK_API_URL_PREFIX", "/")

        if app.config.setdefault("MUCK_APIDOCS_ENABLED", True):
            config = {
                "openapi": openapi_version,
                "specs_route": app.config.setdefault(
                    "MUCK_APIDOCS_URL_PATH", "/apidocs/"
                ),
            }
            if not app.config.setdefault("MUCK_APIDOCS_INTERACTIVE", False):
                config["ui_params"] = {"supportedSubmitMethods": []}
            self.swagger = app.extensions.get("swagger") or Swagger(
                app, config=config, merge=True
            )
            if self.swagger.template:
                self.swagger.template.update(self._spec.to_dict())
            else:
                self.swagger.template = self._spec.to_dict()

        # Add CLI commands
        app.cli.add_command(muck_cli)

    @property
    def openapi_spec_json(self) -> Optional[str]:
        """Returns a json representation of the OpenAPI spec generated by the FlaskMuckApiViews registered."""
        if self._spec:
            return json.dumps(self._spec.to_dict(), indent=2)
        return None

    @property
    def openapi_spec_dict(self) -> Optional[JsonDict]:
        """Returns a dict representation of the OpenAPI spec generated by the FlaskMuckApiViews registered."""
        if self._spec:
            return self._spec.to_dict()
        return None

    def register_muck_views(
        self, muck_views: list[type[FlaskMuckApiView]], app: Optional[Flask] = None
    ) -> None:
        for view in muck_views:
            if view not in self.registered_views:
                register_muck_view(
                    muck_view=view,
                    api=app or current_app,
                    api_spec=self._spec,
                    url_prefix=self.url_prefix,
                )
                self.registered_views.append(view)

                # Refresh the Swagger template.
                if self.swagger:
                    self.swagger.template = self._spec.to_dict()