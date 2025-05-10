from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
import subprocess
import os
import json
import time
from typing import Dict, List, Optional, Union, Any


class ProjectCache:
    def __init__(self, cache_duration: float) -> None:
        self.cache_file: str = os.path.expanduser(
            "~/.cache/ulauncher-git-code-launch/projects_cache.json"
        )
        self.cache_duration: float = cache_duration
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)

    def get_cached_projects(self, root_folder: str) -> Optional[List[str]]:
        try:
            with open(self.cache_file, "r") as f:
                cache_data: Dict[str, Any] = json.load(f)
                timestamp: float = float(cache_data.get("timestamp", 0))
                if (
                    cache_data.get("root_folder") == root_folder
                    and time.time() - timestamp < self.cache_duration
                ):
                    return cache_data.get("projects", [])
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            pass
        return None

    def cache_projects(self, root_folder: str, projects: List[str]) -> None:
        cache_data: Dict[str, Union[str, float, List[str]]] = {
            "root_folder": root_folder,
            "timestamp": time.time(),
            "projects": projects,
        }
        with open(self.cache_file, "w") as f:
            json.dump(cache_data, f)


class ProjectMetadataCollector:
    @staticmethod
    def get_project_metadata(
        project_path: str,
    ) -> Dict[str, Optional[Union[str, bool]]]:
        metadata: Dict[str, Optional[Union[str, bool]]] = {
            "last_commit": None,
            "branch": None,
            "uncommitted_changes": False,
        }
        try:
            last_commit: str = subprocess.check_output(
                [
                    "git",
                    "-C",
                    project_path,
                    "log",
                    "-1",
                    "--format=%cd",
                    "--date=relative",
                ],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            metadata["last_commit"] = last_commit
            branch: str = subprocess.check_output(
                ["git", "-C", project_path, "rev-parse", "--abbrev-ref", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            metadata["branch"] = branch
            status_output: str = subprocess.check_output(
                ["git", "-C", project_path, "status", "--porcelain"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            metadata["uncommitted_changes"] = bool(status_output.strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return metadata


class CursorLauncherExtension(Extension):
    def __init__(self) -> None:
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(
        self, event: KeywordQueryEvent, extension: CursorLauncherExtension
    ) -> RenderResultListAction:
        root_folder: str = os.path.expanduser(extension.preferences["root_folder"])
        try:
            cache_duration: float = float(
                extension.preferences.get("cache_duration", 3600)
            )
        except (TypeError, ValueError):
            cache_duration = 3600
        editors_pref = extension.preferences.get("editors", "code,cursor")
        editors = [e.strip() for e in editors_pref.split(",") if e.strip()]
        # Read confidence threshold from preferences
        try:
            confidence_threshold = float(
                extension.preferences.get("confidence_threshold", 0.1)
            )
        except (TypeError, ValueError):
            confidence_threshold = 0.1
        project_cache: ProjectCache = ProjectCache(cache_duration)
        projects: Optional[List[str]] = project_cache.get_cached_projects(root_folder)
        # If cache miss, do a normal regex search for .git dirs
        if projects is None:
            search_command: str = f"find {root_folder} -type d -name .git -prune -exec dirname {{}} \; | rev | cut -d'/' -f1 | rev"
            try:
                result: subprocess.CompletedProcess = subprocess.run(
                    ["sh", "-c", search_command],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                output: str = result.stdout.strip()
                projects = output.split("\n") if output else []
                project_cache.cache_projects(root_folder, projects)
            except (subprocess.CalledProcessError, FileNotFoundError):
                projects = []
        query: str = event.get_argument() or ""
        filtered_projects: List[str] = []
        confidence_score = 0
        if not query:
            filtered_projects = projects
            confidence_score = 1
        else:
            for project in projects:
                if query.startswith("!"):
                    if query[1:].lower() not in project.lower():
                        filtered_projects.append(project)
                elif query.startswith(">"):
                    full_path: str = os.path.join(root_folder, project)
                    metadata: Dict[str, Optional[Union[str, bool]]] = (
                        ProjectMetadataCollector.get_project_metadata(full_path)
                    )
                    if metadata["uncommitted_changes"]:
                        filtered_projects.append(project)
                elif query.startswith("@"):
                    full_path: str = os.path.join(root_folder, project)
                    metadata: Dict[str, Optional[Union[str, bool]]] = (
                        ProjectMetadataCollector.get_project_metadata(full_path)
                    )
                    if (
                        metadata["branch"]
                        and query[1:].lower() in metadata["branch"].lower()
                    ):
                        filtered_projects.append(project)
                else:
                    if query.lower() in project.lower():
                        filtered_projects.append(project)
            # Calculate confidence score for normal search
            if projects:
                confidence_score = len(filtered_projects) / len(projects)
            else:
                confidence_score = 0
        if confidence_score < confidence_threshold:
            filtered_projects = projects
        projects_to_show: List[str] = filtered_projects or projects
        projects_to_show = projects_to_show[:10]
        items: List[ExtensionResultItem] = []
        # Editor icon mapping
        editor_icons = {
            "code": "images/vscode.png",
            "cursor": "images/cursor.png",
            "subl": "images/sublime.png",
            "idea": "images/intellij.png",
            "pycharm": "images/pycharm.png",
            "clion": "images/clion.png",
            "webstorm": "images/webstorm.png",
            "goland": "images/goland.png",
            "phpstorm": "images/phpstorm.png",
        }
        for project in projects_to_show:
            if project:
                full_path: str = os.path.join(root_folder, project)
                metadata: Dict[str, Optional[Union[str, bool]]] = (
                    ProjectMetadataCollector.get_project_metadata(full_path)
                )
                description_parts: List[str] = []
                if metadata["branch"]:
                    description_parts.append(f"Branch: {metadata['branch']}")
                if metadata["last_commit"]:
                    description_parts.append(f"Last Commit: {metadata['last_commit']}")
                if metadata["uncommitted_changes"]:
                    description_parts.append("⚠️ Uncommitted Changes")
                description: str = " | ".join(description_parts)
                # Pass project path and name as data for next step
                items.append(
                    ExtensionResultItem(
                        icon="images/icon.png",
                        name=project,
                        description=description,
                        on_enter=RenderResultListAction(
                            [
                                ExtensionResultItem(
                                    icon=editor_icons.get(
                                        editor.split()[0], "images/icon.png"
                                    ),
                                    name=editor,
                                    description=f"Open {project} with {editor}",
                                    on_enter=RunScriptAction(
                                        f'bash -l -c "{editor} "{full_path}""'
                                    ),
                                )
                                for editor in editors
                            ]
                        ),
                    )
                )
        if not projects_to_show:
            items.append(
                ExtensionResultItem(
                    icon="images/icon.png",
                    name="No projects found",
                    description="No projects found matching your search",
                    on_enter=HideWindowAction(),
                )
            )
        return RenderResultListAction(items)


class ItemEnterEventListener(EventListener):
    def on_event(self, event: ItemEnterEvent, extension: CursorLauncherExtension):
        # Not used, as we handle editor selection inline with RenderResultListAction
        return HideWindowAction()


if __name__ == "__main__":
    CursorLauncherExtension().run()
