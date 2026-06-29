"""AssetEngine:按 tag 交集打分为 slide 绑定背景素材,带 safe_area(见 DATA_MODEL §5)。

规则匹配(可解释、确定性),不调 LLM、不做向量检索。无命中则不绑 —— 渲染安全回退纯色。

另外提供 `resolve_icon`:把语义关键词解析成预制 Lucide 图标 PNG 的 object_key(纯规则,
延续打分风格)。图标由构建脚本 scripts/build_icons.py 产出(换好主题色的透明 PNG +
keyword_index.json + manifest.json);本引擎只读索引、不做栅格化(packages 零基础设施依赖)。
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from packages.asset_engine.loader import load_index
from packages.asset_engine.models import AssetIndexEntry
from packages.core import AssetBinding, AssetSpec, DeckSpec, SlideSpec

DEFAULT_INDEX_PATH = Path(__file__).resolve().parents[2] / "assets" / "asset_index.json"
# 图标库目录(相对 assets/):构建脚本产出的 PNG + keyword_index.json + manifest.json
_ICON_REL_DIR = Path("icons") / "lucide"

# 默认给 cover/section 配背景;其它页仅当带 asset_hint。
_BACKGROUND_TYPES = ("cover", "section")

# 中文/额外英文语义词 → Lucide 图标名(与 scripts/build_icons.py 的别名表同源,运行期解析用)。
# keyword_index.json 里已含图标名/分词/lucide tags;这里补「关键词派生」最常见的同义词。
_ICON_KEYWORD_ALIASES: dict[str, str] = {
    "growth": "trending-up", "增长": "trending-up", "提升": "trending-up", "趋势": "trending-up",
    "security": "shield", "安全": "shield", "防护": "shield", "保障": "shield",
    "risk": "triangle-alert", "风险": "triangle-alert", "挑战": "triangle-alert",
    "data": "database", "数据": "database", "存储": "database",
    "metric": "chart-column", "指标": "chart-column", "分析": "chart-column", "统计": "chart-column",
    "team": "users", "团队": "users", "用户": "users", "受众": "users", "协作": "users",
    "speed": "zap", "速度": "zap", "效率": "zap", "性能": "gauge", "performance": "gauge",
    "quality": "award", "质量": "award", "成果": "trophy", "成就": "trophy",
    "cost": "coins", "成本": "coins", "费用": "coins", "预算": "wallet", "营收": "coins",
    "business": "handshake", "商业": "handshake", "合作": "handshake",
    "idea": "lightbulb", "想法": "lightbulb", "创新": "lightbulb", "亮点": "sparkles",
    "process": "workflow", "流程": "workflow", "步骤": "workflow", "pipeline": "workflow",
    "compare": "git-compare", "对比": "git-compare", "比较": "git-compare", "权衡": "scale",
    "goal": "target", "目标": "target", "方向": "compass", "战略": "compass", "规划": "compass",
    "time": "clock", "时间": "clock", "进度": "clock", "计划": "calendar", "周期": "calendar",
    "tech": "cpu", "技术": "cpu", "代码": "code", "开发": "code", "架构": "layers", "层级": "layers",
    "system": "settings", "系统": "settings", "配置": "settings", "设置": "settings",
    "云": "cloud", "网络": "network", "服务器": "server",
    "launch": "rocket", "上线": "rocket", "发布": "rocket", "启动": "rocket",
    "工具": "wrench", "维护": "wrench", "解决": "wrench",
    "完成": "circle-check", "验证": "circle-check", "确认": "circle-check", "通过": "circle-check",
    "市场": "globe", "全球": "globe", "国际": "globe",
    "沟通": "message-square", "反馈": "message-square", "通知": "bell",
    "文档": "file-text", "报告": "file-text", "里程碑": "flag", "重点": "flag",
    "集成": "link", "连接": "link", "模块": "puzzle", "整合": "puzzle",
    # Web / 教学 / 工程常见语义(覆盖目录/小结里高频出现的词,提升图标命中率)
    "视图": "eye", "界面": "eye", "展示": "eye", "浏览": "eye", "预览": "eye",
    "路由": "network", "接口": "link", "请求": "send", "响应": "send", "调用": "send",
    "模板": "file-text", "表单": "file-text", "页面": "file-text", "字段": "file-text",
    "登录": "key", "注册": "key", "认证": "lock", "密码": "lock", "加密": "lock", "鉴权": "lock",
    "后台": "server", "服务": "server", "部署": "rocket", "运维": "server",
    "测试": "circle-check", "校验": "circle-check", "检查": "circle-check",
    "搜索": "search", "查询": "search", "检索": "search", "筛选": "filter", "过滤": "filter",
    "文件": "folder", "目录": "folder", "静态": "folder",
    "模型": "box", "对象": "box", "实体": "box", "迁移": "git-branch", "版本": "git-branch", "分支": "git-branch",
    "函数": "code", "变量": "code", "语法": "code", "编程": "code", "脚本": "code",
    "中间件": "layers", "组件": "puzzle", "插件": "puzzle", "扩展": "puzzle", "队列": "layers",
    "位置": "map-pin", "地址": "map-pin", "路线": "map-pin",
    "推荐": "thumbs-up", "点赞": "thumbs-up", "收藏": "star", "评分": "star", "喜欢": "heart",
    "监控": "gauge", "日志": "file-text", "错误": "triangle-alert", "异常": "triangle-alert", "告警": "triangle-alert",
    # 英文/缩写(tokenizer 已小写):Web 后端高频词
    "orm": "database", "sql": "database", "crud": "database", "cache": "database",
    "api": "link", "rest": "link", "url": "link", "http": "network", "https": "network",
    "auth": "lock", "login": "key", "token": "key", "admin": "settings",
    "test": "circle-check", "deploy": "rocket", "docker": "package", "git": "git-branch",
}

# 中文别名按长度降序(子串匹配时优先命中更具体的长词,如「性能」先于「能」)。
_ALIASES_BY_LEN: list[str] = sorted(
    (a for a in _ICON_KEYWORD_ALIASES if not a.isascii()), key=len, reverse=True
)


def _tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    return {t for t in re.split(r"[^0-9a-zA-Z一-鿿]+", text.lower()) if t}


def _tokens_ordered(text: str | None) -> list[str]:
    """保序分词(保留出现次序,用于「取首个命中的图标」更贴近语义重心)。"""
    if not text:
        return []
    return [t for t in re.split(r"[^0-9a-zA-Z一-鿿]+", text.lower()) if t]


def _normhex(value: str) -> str:
    return value.lstrip("#").lower()[:6]


class _IconLibrary:
    """预制图标索引(只读 keyword_index.json + manifest.json),提供「关键词+颜色→object_key」。"""

    def __init__(self, assets_dir: Path) -> None:
        self._dir = assets_dir / _ICON_REL_DIR
        self._keyword_index: dict[str, list[str]] = {}
        self._icons: set[str] = set()
        self._colors: set[str] = set()
        self._load()

    def _load(self) -> None:
        try:
            self._keyword_index = json.loads(
                (self._dir / "keyword_index.json").read_text(encoding="utf-8")
            )
            manifest = json.loads((self._dir / "manifest.json").read_text(encoding="utf-8"))
            self._icons = set(manifest.get("icons", []))
            self._colors = {_normhex(c) for c in manifest.get("colors", [])}
        except (OSError, json.JSONDecodeError):
            # 图标库未构建(没跑 scripts/build_icons.py)→ 静默空库,渲染回退徽章。
            self._keyword_index = {}

    @property
    def available(self) -> bool:
        return bool(self._icons and self._colors)

    def _candidate_icons(self, keyword: str | None) -> list[str]:
        """关键词 → 候选图标名(保序去重):别名表 / keyword_index 命中。

        英文按分词精确命中;中文标题无空格(整段成一个 token),故对中文 token 走「别名子串」
        匹配(长别名优先,更具体),让「增长趋势分析」也能落到 trending-up。
        """
        out: list[str] = []

        def push(name: str) -> None:
            if name in self._icons and name not in out:
                out.append(name)

        for tok in _tokens_ordered(keyword):
            if (aliased := _ICON_KEYWORD_ALIASES.get(tok)) is not None:
                push(aliased)
            for name in self._keyword_index.get(tok, []):
                push(name)
            if not tok.isascii():  # 中文整段 token:按别名子串匹配(长别名优先)
                for alias in _ALIASES_BY_LEN:
                    if alias in tok:
                        push(_ICON_KEYWORD_ALIASES[alias])
        return out

    def resolve(self, keyword: str | None, color_hex: str) -> str | None:
        """关键词 + 期望颜色 → 图标 PNG 的 object_key;颜色未预制或无命中则 None。"""
        if not self.available:
            return None
        hexc = _normhex(color_hex)
        if hexc not in self._colors:
            return None
        for name in self._candidate_icons(keyword):
            return (_ICON_REL_DIR / f"{name}__{hexc}.png").as_posix()
        return None


@lru_cache(maxsize=8)
def _icon_library(assets_dir: Path) -> _IconLibrary:
    return _IconLibrary(assets_dir)


class AssetEngine:
    def __init__(self, index_path: Path | None = None) -> None:
        path = index_path or DEFAULT_INDEX_PATH
        self._backgrounds = [
            e for e in load_index(path).assets if e.asset_type == "background"
        ]
        self._icons = _icon_library(path.parent)

    def resolve_icon(self, keyword: str | None, color_hex: str) -> str | None:
        """语义关键词 + 期望颜色 → 预制图标 PNG 的 object_key;无图标库/无命中则 None。

        color_hex 取自主题调色板(卡片徽章用 background 色压在 primary 圆上、流程用 accent 色),
        构建脚本已按各主题色预制对应 PNG;颜色未预制或语义无命中则返回 None → 渲染回退徽章。
        """
        return self._icons.resolve(keyword, color_hex)

    def bind(self, deck: DeckSpec) -> AssetSpec:
        """为合适的 slide 绑定背景,产出 AssetSpec(无命中的页不绑)。"""
        bindings: list[AssetBinding] = []
        mood = {m.lower() for m in deck.theme.mood}
        topic_tokens = _tokenize(deck.topic)
        for slide in deck.slides:
            if not self._wants_background(slide):
                continue
            entry = self._best_background(slide, mood, topic_tokens)
            if entry is None:
                continue
            bindings.append(
                AssetBinding(
                    slide_id=slide.id,
                    role="background",
                    object_key=entry.object_key,
                    safe_area=entry.safe_area,
                    needs_overlay=entry.needs_overlay,
                    overlay_opacity=entry.overlay_opacity,
                )
            )
        return AssetSpec(bindings=bindings)

    @staticmethod
    def _wants_background(slide: SlideSpec) -> bool:
        return slide.type in _BACKGROUND_TYPES or bool(slide.asset_hint)

    def _best_background(
        self, slide: SlideSpec, mood: set[str], topic_tokens: set[str]
    ) -> AssetIndexEntry | None:
        hint_tokens = topic_tokens | _tokenize(slide.asset_hint)
        best: AssetIndexEntry | None = None
        best_score = 0
        for entry in self._backgrounds:
            mood_overlap = len(mood & {m.lower() for m in entry.mood_tags})
            tags = {t.lower() for t in entry.domain_tags + entry.mood_tags + entry.color_tags}
            hint_overlap = len(hint_tokens & tags)
            # 仅当主题情绪或检索提示有实质关联才绑;只命中 slide_type 不足以绑。
            if mood_overlap == 0 and hint_overlap == 0:
                continue
            score = 2 * mood_overlap + hint_overlap + (slide.type in entry.best_slide_types)
            if score > best_score:
                best, best_score = entry, score
        return best
