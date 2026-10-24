# -*- coding: utf-8 -*-
"""La traducción del backend solo toca campos de interfaz y está apagada por defecto."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.testclient import TestClient

from videodrome import ui_translation
from videodrome.ui_translation import UiTranslationMiddleware


class TranslationPayloadTests(unittest.TestCase):
    def test_only_ui_fields_are_translated(self):
        payload = {
            "error": "保存失败",
            "message": "已保存",
            "title": "保存失败",
            "tags": ["剧情"],
            "nested": {"detail": "保存失败", "name": "保存失败"},
        }
        with mock.patch.object(ui_translation, "glossary", return_value={"保存失败": "Error al guardar", "已保存": "Guardado"}):
            translated = ui_translation.translate_payload(payload)
        self.assertEqual(translated["error"], "Error al guardar")
        self.assertEqual(translated["message"], "Guardado")
        self.assertEqual(translated["title"], "保存失败")
        self.assertEqual(translated["tags"], ["剧情"])
        self.assertEqual(translated["nested"]["detail"], "Error al guardar")
        self.assertEqual(translated["nested"]["name"], "保存失败")

    def test_unknown_strings_stay_as_they_are(self):
        with mock.patch.object(ui_translation, "glossary", return_value={}):
            self.assertEqual(ui_translation.translate_text("保存失败"), "保存失败")

    def test_a_composed_message_is_translated_when_both_halves_are_known(self):
        table = {"本地磁盘": "Disco local", "未配置挂载点": "Punto de montaje sin configurar"}
        with mock.patch.object(ui_translation, "glossary", return_value=table):
            self.assertEqual(
                ui_translation.translate_text("本地磁盘：未配置挂载点"),
                "Disco local: Punto de montaje sin configurar",
            )

    def test_a_composed_message_stays_whole_when_one_half_is_unknown(self):
        table = {"本地磁盘": "Disco local"}
        with mock.patch.object(ui_translation, "glossary", return_value=table):
            self.assertEqual(
                ui_translation.translate_text("本地磁盘：某个没译过的原因"),
                "本地磁盘：某个没译过的原因",
            )

    def test_a_brand_leading_a_composed_message_is_kept(self):
        table = {"未配置挂载点": "Punto de montaje sin configurar"}
        with mock.patch.object(ui_translation, "glossary", return_value=table):
            self.assertEqual(
                ui_translation.translate_text("CloudDrive · 115：未配置挂载点"),
                "CloudDrive · 115: Punto de montaje sin configurar",
            )


class MiddlewareTests(unittest.TestCase):
    def setUp(self):
        ui_translation.glossary.cache_clear()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.glossary = Path(self.temp.name) / "glossary.json"
        self.glossary.write_text(json.dumps({"保存失败": "Error al guardar"}, ensure_ascii=False), encoding="utf-8")
        self.env = mock.patch.dict(os.environ, {
            "PEACH_LOCALE": "es",
            "PEACH_I18N_GLOSSARY": str(self.glossary),
        }, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(ui_translation.glossary.cache_clear)

        self.app = FastAPI()
        self.app.add_middleware(UiTranslationMiddleware)

        @self.app.get("/api/error")
        def error():
            return JSONResponse({"error": "保存失败", "title": "保存失败", "count": 1})

        @self.app.get("/api/detail")
        def detail():
            return JSONResponse({"detail": [{"msg": "保存失败", "loc": ["body", "name"]}]})

        @self.app.get("/plain")
        def plain():
            return PlainTextResponse("保存失败")

    def test_json_ui_fields_are_translated_and_data_is_not(self):
        with TestClient(self.app) as client:
            body = client.get("/api/error").json()
        self.assertEqual(body["error"], "Error al guardar")
        self.assertEqual(body["title"], "保存失败")
        self.assertEqual(body["count"], 1)

    def test_nested_validation_messages_are_translated(self):
        with TestClient(self.app) as client:
            body = client.get("/api/detail").json()
        self.assertEqual(body["detail"][0]["msg"], "Error al guardar")
        self.assertEqual(body["detail"][0]["loc"], ["body", "name"])

    def test_non_json_responses_are_untouched(self):
        with TestClient(self.app) as client:
            response = client.get("/plain")
        self.assertEqual(response.text, "保存失败")

    def test_mode_is_off_by_default(self):
        os.environ.pop("PEACH_LOCALE", None)
        with TestClient(self.app) as client:
            body = client.get("/api/error").json()
        self.assertEqual(body["error"], "保存失败")


class MissingGlossaryTests(unittest.TestCase):
    def test_missing_glossary_keeps_the_original_text(self):
        with mock.patch.dict(os.environ, {
            "PEACH_LOCALE": "es",
            "PEACH_I18N_GLOSSARY": "/nonexistent/glossary.json",
        }, clear=False):
            ui_translation.glossary.cache_clear()
            self.assertEqual(ui_translation.translate_text("保存失败"), "保存失败")
        ui_translation.glossary.cache_clear()


class PageShellTests(unittest.TestCase):
    """La cáscara del servidor también sale en español, no solo el JSON."""

    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"PEACH_LOCALE": "es"}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.glossary = mock.patch.object(
            ui_translation, "glossary",
            return_value={"登录 Videodrome": "Iniciar sesión en Videodrome", "数据库正在迁移": "La base de datos se está migrando"},
        )
        self.glossary.start()
        self.addCleanup(self.glossary.stop)

    def test_shell_uses_spanish_locale_title_and_aria_data(self):
        from videodrome.web_entry import page_shell

        html = page_shell("登录 Videodrome", "login", {"error": "数据库正在迁移", "next": "/wants"})
        self.assertIn('lang="es-ES"', html)
        self.assertIn("<title>Iniciar sesión en Videodrome</title>", html)
        self.assertIn("react-aria.i18n.locale", html)
        self.assertIn('data-error="La base de datos se está migrando"', html)
        self.assertIn('data-next="/wants"', html)

    def test_index_shell_is_translated_without_touching_the_source(self):
        html = ('<!doctype html><html lang="zh-CN"><head><title>Videodrome · 蜜桃</title></head>'
                '<body><a href="#main">跳到正文</a>'
                '<input placeholder="搜索馆藏" aria-label="搜索作品">'
                '<h2 data-page-title>首页</h2></body></html>')
        with mock.patch.object(
            ui_translation, "glossary",
            return_value={"跳到正文": "Saltar al contenido", "搜索馆藏": "Buscar en la colección",
                          "搜索作品": "Buscar títulos", "首页": "inicio"},
        ):
            translated = ui_translation.translate_index_html(html)
        self.assertIn('lang="es-ES"', translated)
        self.assertIn("<title>Videodrome</title>", translated)
        self.assertIn("Saltar al contenido", translated)
        self.assertIn('placeholder="Buscar en la colección"', translated)
        self.assertIn('aria-label="Buscar títulos"', translated)
        self.assertIn(">inicio</h2>", translated)
        self.assertIn("react-aria.i18n.locale", translated)
        self.assertNotIn("zh-CN", translated)

    def test_the_code_inside_the_html_is_left_alone(self):
        html = ("<html lang=\"zh-CN\"><body><code>const x = '首页';</code>"
                "<p>首页</p></body></html>")
        with mock.patch.object(ui_translation, "glossary", return_value={"首页": "inicio"}):
            translated = ui_translation.translate_index_html(html)
        self.assertIn("const x = '首页';", translated)
        self.assertIn("<p>inicio</p>", translated)

