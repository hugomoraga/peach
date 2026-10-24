# Guía de traducción zh → es (Peach)

Contexto: Peach 蜜桃 es una app personal de medios (cine/AV/JAV), local-first,
para un solo usuario. La interfaz está en chino y se traduce al español.

## Qué NO se traduce

Estas cadenas son **valores de base de datos**, no texto de interfaz:

- Etiquetas de contenido: 毒龙, 骑乘, 后入, 口罩遮脸, 3P多人, 双洞齐插…
- Géneros: 愛好, 蘿莉塔, 聖夜に一発…
- Títulos de producto: 〇〇ちゃん_vol.1
- Nombres de estudio, nombres de persona Japanese/China
- Kanji, japanese scraped values
- URLs, rutas, claves de configuración, nombres de campo JSON

Regla: si la cadena es un **valor que se guarda o se compara** (tag, genre,
nombre de producto, código), NO se traduce aunque parezca UI.

## Qué sí se traduce

- Etiquetas de botones, menús, títulos de sección
- Mensajes de error y de estado
- Textos de ayuda, descripciones, tooltips, placeholders
- Nombres de páginas y títulos de ventana
- Textos del menú bar (tray) y de la CLI

## Estilo

1. **Tuteo formal neutro** ("usted" implícito), sin voseo ni vosotros.
2. español de España neutro, sin regionalismos marcados.
3. **Conciso**: la UI es densa. Si el chino cabe en 4 caracteres, el español
   debería caber en 1-3 palabras. No alargar.
4. **Consistencia estricta** de términos (tabla abajo).
5. Mantener el registro técnico: "番" (código de producto) → "código";
   "厂牌" → "estudio"; "女优/演员" → "actriz"; "番号" → "código";
   "种子" → "torrent"; "生肉" → "sin procesar"; "磁力" → "magnet".
6. **Placeholders intocables**: `${n}`, `{count}`, `%s`, `{}` se copian tal cual.
   Si el placeholder va dentro de una frase, la frase se adapta al español pero
   el placeholder no cambia.
7. Los términosDependientes de otros no se traducen: nombres de archivo,
   claves JSON, valores de enum, IDs.
8. Mayúscula: botones y títulos en "Sentence case" (首字母 mayúscula, no TODO EN
   MAYÚSCULAS). Los títulos de sección pueden ir en minúscula si el chino lo está.
9. Sin emojis nuevos. No inventar texto que no está.
10. Si el chino es ambiguo, elegir la lectura más natural en contexto de esta app.

## Tabla de términos (obligatoria)

| Chino | Español |
|---|---|
| 媒体库 | biblioteca |
| 馆藏 | colección |
| 作品 | título |
| 女优 | actriz |
| 演员 | actor |
| 厂牌 | estudio |
| 标签 | etiqueta |
| 番号 | código |
| 追剧 / 关注 | seguir |
| 关注源 | fuente seguida |
| 播放墙 | muro de reproducción |
| 沉浸模式 | modo inmersivo |
| 设置 | ajustes |
| 诊断 | diagnóstico |
| 维护 | mantenimiento |
| 下载 | descarga |
| 上传 | subida |
| 清理 | limpieza |
| 整理 | organización |
| 复核 | revisión |
| 候选 | candidata |
| 草稿 | borrador |
| 日志 | registro |
| 任务 | tarea |
| 进度 | progreso |
| 队列 | cola |
| 概览 | resumen |
| 概览 | vista general |
| 同步 | sincronizar |
| 采集 | recolección |
| 刮削 | scraping |
| 元数据 | metadatos |
| 文件名 | nombre de archivo |
| 文件夹 | carpeta |
| 磁盘 | disco |
| 存储 | almacenamiento |
| 密码 | contraseña |
| 账号 | cuenta |
| 登录 | iniciar sesión |
| 退出 | salir |
| 搜索 | buscar |
| 筛选 | filtrar |
| 排序 | ordenar |
| 随机 | aleatorio |
| 播放 | reproducir |
| 暂停 | pausar |
| 继续 | continuar |
| 停止 | detener |
| 重试 | reintentar |
| 全部 | todo |
| 无 | ninguno |
| 已暂停 | pausado |
| 正常 | correcto |
| 未检查 | sin comprobar |
| 检查失败 | error al comprobar |
| 启用 | activar |
| 禁用 | desactivar |
| 未启用 | desactivado |
| 成功 | correcto |
| 失败 | error |
| 警告 | advertencia |
| 确认 | confirmar |
| 取消 | cancelar |
| 删除 | eliminar |
| 恢复 | restaurar |
| 撤销 | deshacer |
| 重置 | restablecer |
| 提交 | enviar |
| 保存 | guardar |
| 应用 | aplicar |
| 复制 | copiar |
| 粘贴 | pegar |
| 剪切 | cortar |
| 导入 | importar |
| 导出 | exportar |
| 添加 | añadir |
| 新建 | nuevo |
| 编辑 | editar |
| 删除 | eliminar |
| 详情 | detalles |
| 简介 | resumen |
| 备注 | nota |
| 名称 | nombre |
| 标题 | título |
| 类型 | tipo |
| 状态 | estado |
| 时间 | hora |
| 日期 | fecha |
| 大小 | tamaño |
| 数量 | cantidad |
| 版本 | versión |
| 更新 | actualizar |
| 更新源 | origen de actualizaciones |
| 未发布 | sin publicar |
| 已发布 | publicado |
| 内存 | memoria |
| 磁盘空间 | espacio en disco |
| 占用 | ocupa |
| 剩余 | restante |
| 缓存 | caché |
| 日志文件 | archivo de registro |
| 订阅 | suscripción |
| 源 | origen |
| 来源 | fuente |
| 目标 | destino |
| 转换 | convertir |
| 转码 | transcodificar |
| 缩略图 | miniatura |
| 封面 | portada |
| 字幕 | subtítulo |
| 弹幕 | comentarios |
| 播放速度 | velocidad de reproducción |
| 音量 | volumen |
| 全屏 | pantalla completa |
| 画中画 | imagen en imagen |
| 清晰度 | calidad |
| 画质 | calidad de imagen |
| 分辨率 | resolución |
| 帧率 | fps |
| 硬件加速 | aceleración por hardware |
| 转录 | transcripción |

## Formato de salida

Un único objeto JSON: `{"<chino>": "<español>"}`. Solo las claves que se
traducen. Si una cadena no se debe traducir (es dato), **no la incluyas**.
Devuelve JSON puro, sin markdown ni explicaciones.
