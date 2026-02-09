"""Skills as markdown files with relevance scoring."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ..core.events import EventLog


class SkillRegistry:
    def __init__(self, skills_dir: Path, event_log: EventLog) -> None:
        self.skills_dir = skills_dir
        self._event_log = event_log
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def _skill_path(self, skill_id: str) -> Path:
        normalized = str(skill_id or "").strip().lower()
        if not normalized:
            raise ValueError("Skill id is required")
        safe = "".join(ch for ch in normalized if ch.isalnum() or ch in {"_", "-"})
        if safe != normalized or not safe:
            raise ValueError("Skill id may only contain lowercase letters, numbers, _ and -")
        path = (self.skills_dir / f"{safe}.md").resolve()
        try:
            path.relative_to(self.skills_dir.resolve())
        except ValueError as exc:
            raise ValueError("Skill path is outside skills directory") from exc
        return path

    def _title_from_content(self, content: str, default_title: str) -> str:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip() or default_title
        return default_title

    def _tokens(self, text: str) -> List[str]:
        words: List[str] = []
        token = []
        for ch in text.lower():
            if ch.isalnum():
                token.append(ch)
                continue
            if token:
                word = "".join(token)
                if len(word) >= 3:
                    words.append(word)
                token = []
        if token:
            word = "".join(token)
            if len(word) >= 3:
                words.append(word)
        return words

    def _extract_declared_keywords(self, content: str) -> List[str]:
        declared: List[str] = []
        for line in content.splitlines()[:40]:
            stripped = line.strip().lower()
            if stripped.startswith("keywords:") or stripped.startswith("- keywords:"):
                raw = stripped.split(":", 1)[1]
                declared.extend([item.strip() for item in raw.split(",") if item.strip()])
        return declared

    def _score_skill_relevance(self, skill: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        text = str(user_message or "").lower()
        if not text.strip():
            return {"apply": False, "score": 0, "reason": "empty_query"}

        skill_id = str(skill.get("id") or "")
        title = str(skill.get("title") or skill_id)
        content = str(skill.get("content") or "")

        if skill_id and f"${skill_id.lower()}" in text:
            return {"apply": True, "score": 999, "reason": "explicit_id_mention"}

        query_tokens = set(self._tokens(text))
        if not query_tokens:
            return {"apply": False, "score": 0, "reason": "no_query_tokens"}

        declared_keywords = self._extract_declared_keywords(content)
        for keyword in declared_keywords:
            if keyword and keyword in text:
                return {"apply": True, "score": 100, "reason": f"declared_keyword:{keyword}"}

        title_tokens = set(self._tokens(title))
        id_tokens = set(self._tokens(skill_id.replace("-", " ").replace("_", " ")))
        content_tokens = self._tokens(content)
        content_focus = set(content_tokens[:120])

        overlap_title = query_tokens.intersection(title_tokens.union(id_tokens))
        overlap_content = query_tokens.intersection(content_focus)
        score = len(overlap_title) * 2 + len(overlap_content)

        return {
            "apply": False,
            "score": score,
            "reason": "token_overlap",
            "title_overlap": sorted(overlap_title),
            "content_overlap": sorted(overlap_content),
        }

    def list(self) -> List[Dict[str, Any]]:
        skills: List[Dict[str, Any]] = []
        for path in sorted(self.skills_dir.glob("*.md")):
            content = path.read_text(encoding="utf-8", errors="replace")
            title = self._title_from_content(content, path.stem)
            skills.append(
                {
                    "id": path.stem,
                    "title": title,
                    "path": str(path),
                    "content": content,
                }
            )
        return skills

    def selected(self, skill_ids: List[str]) -> List[Dict[str, Any]]:
        requested = [str(skill_id).strip() for skill_id in skill_ids if str(skill_id).strip()]
        by_id = {skill["id"]: skill for skill in self.list()}
        selected: List[Dict[str, Any]] = []
        for skill_id in requested:
            skill = by_id.get(skill_id)
            if skill:
                selected.append(skill)
            else:
                self._event_log.add("skill.missing", "Requested skill was not found", {"skill_id": skill_id})
        return selected

    def applicable_for_query(self, skill_ids: List[str], user_message: str, min_score: int = 2) -> List[Dict[str, Any]]:
        candidates = self.selected(skill_ids)
        chosen: List[Dict[str, Any]] = []
        threshold = max(1, int(min_score))
        for skill in candidates:
            relevance = self._score_skill_relevance(skill, user_message)
            apply_skill = bool(relevance.get("apply")) or int(relevance.get("score") or 0) >= threshold
            if apply_skill:
                skill_copy = dict(skill)
                skill_copy["_match"] = relevance
                chosen.append(skill_copy)
                self._event_log.add(
                    "skill.selected",
                    "Skill selected for this query",
                    {
                        "skill": skill["id"],
                        "match": relevance,
                    },
                )
            else:
                self._event_log.add(
                    "skill.skipped",
                    "Skill skipped for this query",
                    {
                        "skill": skill["id"],
                        "match": relevance,
                        "min_score": threshold,
                    },
                )
        return chosen

    def save_markdown_skill(self, skill_id: str, markdown_content: str) -> Dict[str, Any]:
        path = self._skill_path(skill_id)
        content = str(markdown_content or "").rstrip() + "\n"
        path.write_text(content, encoding="utf-8")
        self._event_log.add(
            "skill.saved",
            "Saved markdown skill file",
            {
                "skill_id": path.stem,
                "path": str(path),
            },
        )
        return {
            "id": path.stem,
            "path": str(path),
            "content": content,
        }

    def delete_skill(self, skill_id: str) -> Dict[str, Any]:
        path = self._skill_path(skill_id)
        if not path.exists():
            raise ValueError(f"Skill file not found: {path.stem}")
        path.unlink()
        self._event_log.add(
            "skill.deleted",
            "Deleted markdown skill file",
            {
                "skill_id": path.stem,
                "path": str(path),
            },
        )
        return {
            "id": path.stem,
            "path": str(path),
        }

    def delete_if_exists(self, skill_id: str) -> bool:
        path = self._skill_path(skill_id)
        if not path.exists():
            return False
        path.unlink()
        self._event_log.add(
            "skill.deleted",
            "Deleted markdown skill file",
            {
                "skill_id": path.stem,
                "path": str(path),
            },
        )
        return True

    def seed_defaults(self, templates: Dict[str, str]) -> List[str]:
        created: List[str] = []
        for skill_id, content in templates.items():
            path = self._skill_path(skill_id)
            if path.exists():
                continue
            normalized = str(content or "").rstrip() + "\n"
            path.write_text(normalized, encoding="utf-8")
            created.append(skill_id)
            self._event_log.add(
                "skill.seeded",
                "Created default skill file",
                {
                    "skill_id": skill_id,
                    "path": str(path),
                },
            )
        return created
