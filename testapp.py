#!/usr/bin/env python3
"""brAIndance - Quiz Management and Generation System.

Single-page application (index.html + app.js) served by a stdlib-only
Python backend exposing a small JSON API. Topics are persisted as JSON
files in topics/. Implements the UML class diagram classes:
DifficultyLevel, Question, Topic, TopicFileManager, Quiz, QuizResult,
QuizGenerator, User. No pip install required.
"""

import json
import os
import uuid
import webbrowser
from enum import Enum
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Optional
from urllib.parse import quote, unquote, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIRECTORY = os.path.join(BASE_DIR, "topics")
HOST = os.environ.get("QUIZ_APP_HOST", "127.0.0.1")
PORT = int(os.environ.get("QUIZ_APP_PORT", "8001"))

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/logo.png": ("logo.png", "image/png"),
}


# --------------------------------------------------------------------------
# 1. Enum: DifficultyLevel
# --------------------------------------------------------------------------

class DifficultyLevel(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

    @staticmethod
    def from_value(value: str) -> "DifficultyLevel":
        if value:
            string = str(value).lower()
            for level in DifficultyLevel:
                if level.value == string:
                    return level
        return DifficultyLevel.MEDIUM

    @staticmethod
    def all() -> List["DifficultyLevel"]:
        return [DifficultyLevel.EASY, DifficultyLevel.MEDIUM, DifficultyLevel.HARD]


# --------------------------------------------------------------------------
# 2. Class: Question  (two-option multiple choice)
# --------------------------------------------------------------------------

class Question:
    def __init__(self, question_id: str, prompt: str,
                 option_a: str, option_b: str,
                 correct: int = 0,
                 difficulty: Optional["DifficultyLevel"] = None):
        self._questionId = question_id
        self._prompt = prompt
        self._options: List[str] = [option_a, option_b]
        self._correct = 1 if correct else 0
        self._difficulty = difficulty if difficulty is not None else DifficultyLevel.EASY

    def get_question_id(self) -> str:
        return self._questionId

    def get_question_text(self) -> str:
        return self._prompt

    def set_question_text(self, text: str) -> None:
        self._prompt = text

    def get_prompt(self) -> str:
        return self._prompt

    def get_options(self) -> List[str]:
        return list(self._options)

    def set_options(self, option_a: str, option_b: str) -> None:
        self._options = [option_a, option_b]

    def get_correct(self) -> int:
        return self._correct

    def set_correct(self, index: int) -> None:
        self._correct = 1 if index else 0

    def get_difficulty(self) -> DifficultyLevel:
        return self._difficulty

    def set_difficulty(self, difficulty: DifficultyLevel) -> None:
        self._difficulty = difficulty

    def to_dict(self) -> dict:
        return {
            "id": self._questionId,
            "prompt": self._prompt,
            "options": list(self._options),
            "correct": self._correct,
            "diff": self._difficulty.value,
        }

    @staticmethod
    def from_dict(data: dict) -> "Question":
        question_id = data.get("id") or data.get("questionId") or uuid.uuid4().hex
        prompt = data.get("prompt") or data.get("questionText") or ""
        options = data.get("options")
        if not isinstance(options, list) or len(options) < 2:
            options = [data.get("answerText") or "", "Not this one"]
        correct = data.get("correct", 0)
        correct = 1 if correct is True or str(correct).strip() == "1" else 0
        difficulty = DifficultyLevel.from_value(data.get("diff") or data.get("difficulty"))
        return Question(question_id, prompt, str(options[0]), str(options[1]),
                        correct, difficulty)


# --------------------------------------------------------------------------
# 3. Class: Topic
# --------------------------------------------------------------------------

class Topic:
    def __init__(self, topic_id: str, topic_name: str,
                 questions: Optional[List[Question]] = None):
        self._topicId = topic_id
        self._topicName = topic_name
        self._questions: List[Question] = questions if questions is not None else []

    def get_topic_id(self) -> str:
        return self._topicId

    def get_topic_name(self) -> str:
        return self._topicName

    def set_topic_name(self, name: str) -> None:
        self._topicName = name

    def add_question(self, question: Question) -> None:
        self._questions.append(question)

    def modify_question(self, question_id: str, prompt: str,
                        option_a: str, option_b: str,
                        correct: int, difficulty: DifficultyLevel) -> bool:
        for question in self._questions:
            if question.get_question_id() == question_id:
                question.set_question_text(prompt)
                question.set_options(option_a, option_b)
                question.set_correct(correct)
                question.set_difficulty(difficulty)
                return True
        return False

    def delete_question(self, question_id: str) -> bool:
        for question in self._questions:
            if question.get_question_id() == question_id:
                self._questions.remove(question)
                return True
        return False

    def filter_by_difficulty(self, difficulty: DifficultyLevel) -> List[Question]:
        return [q for q in self._questions if q.get_difficulty() == difficulty]

    def get_questions(self) -> List[Question]:
        return self._questions

    def to_dict(self) -> dict:
        return {
            "id": self._topicId,
            "name": self._topicName,
            "questions": [q.to_dict() for q in self._questions],
        }

    @staticmethod
    def from_dict(data: dict) -> "Topic":
        topic_id = data.get("id") or data.get("topicId") or uuid.uuid4().hex
        topic_name = data.get("name") or data.get("topicName") or "Untitled Topic"
        questions = [Question.from_dict(q) for q in (data.get("questions") or [])]
        return Topic(topic_id, topic_name, questions)


# --------------------------------------------------------------------------
# 4. Class: TopicFileManager
# --------------------------------------------------------------------------

class TopicFileManager:
    def __init__(self, storage_directory: str):
        self._storageDirectory = storage_directory
        os.makedirs(self._storageDirectory, exist_ok=True)

    @staticmethod
    def _sanitize(topic_name: str) -> str:
        clean = "".join(ch if ch.isalnum() else "_" for ch in topic_name)
        return clean.strip("_") or "topic"

    def _file_path(self, topic_name: str, extension: str = ".json") -> str:
        return os.path.join(self._storageDirectory,
                            self._sanitize(topic_name) + extension)

    def load_all_topics(self) -> List[Topic]:
        topics: List[Topic] = []
        for file_name in sorted(os.listdir(self._storageDirectory)):
            if not file_name.endswith(".json"):
                continue
            path = os.path.join(self._storageDirectory, file_name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            try:
                topic = Topic.from_dict(data)
            except (KeyError, TypeError, ValueError):
                continue
            if "topicId" in data or "topicName" in data:
                # Legacy free-text format -> migrate to the two-option format.
                try:
                    self.save_topic_to_file(topic)
                except OSError:
                    pass
            topics.append(topic)
        return topics

    def load_by_id(self, topic_id: str) -> Optional[Topic]:
        for topic in self.load_all_topics():
            if topic.get_topic_id() == topic_id:
                return topic
        return None

    def save_topic_to_file(self, topic: Topic, file_format: str = "json") -> bool:
        file_format = (file_format or "json").lower()
        try:
            if file_format == "text":
                path = self._file_path(topic.get_topic_name(), ".txt")
                lines = [f"Topic: {topic.get_topic_name()}",
                         f"Topic ID: {topic.get_topic_id()}"]
                for index, q in enumerate(topic.get_questions(), start=1):
                    correct = q.get_options()[q.get_correct()] if q.get_options() else ""
                    lines.append(f"{index}. [{q.get_difficulty().value}] "
                                 f"{q.get_question_text()}  =>  {correct}")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
            else:
                path = self._file_path(topic.get_topic_name(), ".json")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(topic.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except OSError:
            return False

    def delete_topic_file(self, topic_name: str) -> bool:
        path = self._file_path(topic_name, ".json")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def delete_by_id(self, topic_id: str) -> bool:
        for topic in self.load_all_topics():
            if topic.get_topic_id() == topic_id:
                return self.delete_topic_file(topic.get_topic_name())
        return False


# --------------------------------------------------------------------------
# 5. Class: QuizResult
# --------------------------------------------------------------------------

class QuizResult:
    def __init__(self, topic_name: str, difficulty: DifficultyLevel,
                 score: int, percentage: float,
                 correct_answers: List[str]):
        self._topicName = topic_name
        self._difficulty = difficulty
        self._score = score
        self._percentage = percentage
        self._correctAnswers = correct_answers

    def get_topic_name(self) -> str:
        return self._topicName

    def get_difficulty(self) -> DifficultyLevel:
        return self._difficulty

    def get_score(self) -> int:
        return self._score

    def get_percentage(self) -> float:
        return self._percentage

    def get_correct_answers(self) -> List[str]:
        return self._correctAnswers

    def display_summary(self) -> str:
        return (
            f"Topic: {self._topicName}\n"
            f"Difficulty: {self._difficulty.value.capitalize()}\n"
            f"Score: {self._score}\n"
            f"Percentage: {self._percentage:.1f}%"
        )


# --------------------------------------------------------------------------
# 6. Class: Quiz
# --------------------------------------------------------------------------

class Quiz:
    def __init__(self):
        self._quizId = uuid.uuid4().hex
        self._topic: Optional[Topic] = None
        self._topicName: str = ""
        self._selectedDifficulty: DifficultyLevel = DifficultyLevel.MEDIUM
        self._questions: List[Question] = []
        self._userAnswers: Dict[str, int] = {}
        self._score = 0
        self._percentage = 0.0

    def get_quiz_id(self) -> str:
        return self._quizId

    def get_topic(self) -> Optional[Topic]:
        return self._topic

    def get_selected_difficulty(self) -> DifficultyLevel:
        return self._selectedDifficulty

    def get_questions(self) -> List[Question]:
        return self._questions

    def get_user_answers(self) -> Dict[str, int]:
        return self._userAnswers

    def get_score(self) -> int:
        return self._score

    def get_percentage(self) -> float:
        return self._percentage

    def set_topic(self, topic: Topic) -> None:
        self._topic = topic

    def select_topic(self, topic_name: str) -> None:
        self._topicName = topic_name

    def select_difficulty(self, level: DifficultyLevel) -> None:
        self._selectedDifficulty = level

    def start_quiz(self) -> List[Question]:
        if self._topic is not None:
            self._questions = self._topic.filter_by_difficulty(self._selectedDifficulty)
        else:
            self._questions = []
        return self._questions

    def submit_answer(self, question_id: str, answer: int) -> None:
        self._userAnswers[question_id] = answer

    def generate_result(self) -> QuizResult:
        correct: List[str] = []
        for question in self._questions:
            given = self._userAnswers.get(question.get_question_id())
            try:
                given_index = int(given)
            except (TypeError, ValueError):
                given_index = -1
            if given_index == question.get_correct():
                correct.append(question.get_question_text())
        total = len(self._questions)
        self._score = len(correct)
        self._percentage = (self._score / total * 100.0) if total else 0.0
        topic_name = self._topicName or (self._topic.get_topic_name() if self._topic else "")
        return QuizResult(
            topic_name=topic_name,
            difficulty=self._selectedDifficulty,
            score=self._score,
            percentage=self._percentage,
            correct_answers=correct,
        )


# --------------------------------------------------------------------------
# 7. Class: QuizGenerator
# --------------------------------------------------------------------------

class QuizGenerator:
    def __init__(self, file_manager: TopicFileManager):
        self._fileManager = file_manager

    def generate_quiz(self, topic: Topic,
                      difficulty: DifficultyLevel) -> Quiz:
        quiz = Quiz()
        quiz.select_topic(topic.get_topic_name())
        quiz.set_topic(topic)
        quiz.select_difficulty(difficulty)
        quiz.start_quiz()
        return quiz


# --------------------------------------------------------------------------
# 8. Class: User
# --------------------------------------------------------------------------

class User:
    def __init__(self, user_id: str, username: str):
        self._userId = user_id
        self._username = username
        self._quiz: Optional[Quiz] = None

    def get_user_id(self) -> str:
        return self._userId

    def get_username(self) -> str:
        return self._username

    def set_username(self, username: str) -> None:
        self._username = username

    def get_quiz(self) -> Optional[Quiz]:
        return self._quiz

    def set_quiz(self, quiz: Quiz) -> None:
        self._quiz = quiz

    def select_topic(self, topic_name: str) -> None:
        if self._quiz is not None:
            self._quiz.select_topic(topic_name)

    def select_difficulty(self, level: DifficultyLevel) -> None:
        if self._quiz is not None:
            self._quiz.select_difficulty(level)

    def start_quiz(self) -> None:
        if self._quiz is not None:
            self._quiz.start_quiz()

    def submit_answer(self, question_id: str, answer: int) -> None:
        if self._quiz is not None:
            self._quiz.submit_answer(question_id, answer)

    def manage_topic(self) -> None:
        """Interface point for topic/question CRUD operations.

        Delegated to TopicFileManager and the JSON API in the web UI.
        """


# --------------------------------------------------------------------------
# HTTP Server + JSON API request handler
# --------------------------------------------------------------------------

class QuizAppServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address, handler_class, file_manager: TopicFileManager):
        super().__init__(server_address, handler_class)
        self.file_manager = file_manager
        self.sessions: Dict[str, dict] = {}


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "QuizApp/1.0"

    def __init__(self, *args, **kwargs):
        self._pending_cookies = []
        super().__init__(*args, **kwargs)

    # -- helpers ----------------------------------------------------------

    def app(self) -> QuizAppServer:
        return self.server

    def _session(self) -> dict:
        sid = None
        saved_name = None
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("quiz_sid="):
                sid = part.split("=", 1)[1]
            elif part.startswith("display_name="):
                saved_name = unquote(part.split("=", 1)[1])
        if not sid or sid not in self.app().sessions:
            sid = uuid.uuid4().hex
            username = saved_name.strip() if saved_name and saved_name.strip() else "Guest"
            self.app().sessions[sid] = {"user": User("user-" + sid[:8], username)}
            self._pending_cookies.append(f"quiz_sid={sid}; Path=/")
        return self.app().sessions[sid]

    def _send_cookie(self) -> None:
        for cookie in getattr(self, "_pending_cookies", []):
            self.send_header("Set-Cookie", cookie)
        self._pending_cookies = []

    def _json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            data = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _api_segments(path: str, prefix: str):
        if path == prefix or path == prefix + "/":
            return []
        if path.startswith(prefix + "/"):
            return [unquote(segment) for segment in path[len(prefix) + 1:].split("/")]
        return None

    def _send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._send_cookie()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_static(self, rel_path: str, content_type: str) -> None:
        full = os.path.join(BASE_DIR, rel_path)
        if not os.path.exists(full):
            return self._send_json({"error": "Not found"}, 404)
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self._send_cookie()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _topics_payload(self) -> dict:
        return {"topics": [t.to_dict() for t in self.app().file_manager.load_all_topics()]}

    def log_message(self, fmt, *args):
        print(f"[quiz] {self.address_string()} - {fmt % args}")

    # -- routes -----------------------------------------------------------

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        self._session()

        if path == "/api/topics":
            return self._send_json(self._topics_payload())
        if path == "/api/account":
            user = self._session()["user"]
            return self._send_json({"username": user.get_username(),
                                    "user_id": user.get_user_id()})
        if path in STATIC_FILES:
            rel_path, content_type = STATIC_FILES[path]
            return self._send_static(rel_path, content_type)
        self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._json_body()
        self._session()

        if path == "/api/topics":
            return self._api_create_topic(body)
        if path == "/api/account":
            return self._api_save_account(body)
        if path == "/api/quizzes":
            return self._api_submit_quiz(body)
        segments = self._api_segments(path, "/api/topics")
        if segments and len(segments) == 2 and segments[1] == "questions":
            return self._api_add_question(segments[0], body)
        self._send_json({"error": "Not found"}, 404)

    def do_PUT(self):
        path = urlparse(self.path).path
        body = self._json_body()
        self._session()
        segments = self._api_segments(path, "/api/topics")
        if segments and len(segments) == 3 and segments[1] == "questions":
            return self._api_modify_question(segments[0], segments[2], body)
        self._send_json({"error": "Not found"}, 404)

    def do_DELETE(self):
        path = urlparse(self.path).path
        self._session()
        segments = self._api_segments(path, "/api/topics")
        if segments and len(segments) == 3 and segments[1] == "questions":
            return self._api_delete_question(segments[0], segments[2])
        if segments and len(segments) == 1:
            return self._api_delete_topic(segments[0])
        self._send_json({"error": "Not found"}, 404)

    # -- API implementations ---------------------------------------------

    def _api_create_topic(self, body: dict) -> None:
        name = (body.get("name") or "").strip()
        if not name:
            return self._send_json({"error": "Topic name cannot be empty."}, 400)
        topics = self.app().file_manager.load_all_topics()
        if any(t.get_topic_name().lower() == name.lower() for t in topics):
            return self._send_json({"error": f"Topic '{name}' already exists."}, 409)
        topic = Topic(uuid.uuid4().hex, name)
        if not self.app().file_manager.save_topic_to_file(topic):
            return self._send_json({"error": "Failed to save topic file."}, 500)
        self._send_json(self._topics_payload())

    def _api_add_question(self, topic_id: str, body: dict) -> None:
        prompt = (body.get("prompt") or "").strip()
        option_a = (body.get("optionA") or "").strip()
        option_b = (body.get("optionB") or "").strip()
        if not prompt or not option_a or not option_b:
            return self._send_json({"error": "Prompt and both options are required."}, 400)
        correct = body.get("correct")
        correct = 1 if correct is True or str(correct).strip() == "1" else 0
        difficulty = DifficultyLevel.from_value(body.get("diff"))
        topic = self.app().file_manager.load_by_id(topic_id)
        if topic is None:
            return self._send_json({"error": "Topic not found."}, 404)
        topic.add_question(Question(uuid.uuid4().hex, prompt, option_a, option_b,
                                    correct, difficulty))
        self.app().file_manager.save_topic_to_file(topic)
        self._send_json(self._topics_payload())

    def _api_modify_question(self, topic_id: str, question_id: str,
                             body: dict) -> None:
        prompt = (body.get("prompt") or "").strip()
        option_a = (body.get("optionA") or "").strip()
        option_b = (body.get("optionB") or "").strip()
        if not prompt or not option_a or not option_b:
            return self._send_json({"error": "Prompt and both options are required."}, 400)
        correct = body.get("correct")
        correct = 1 if correct is True or str(correct).strip() == "1" else 0
        difficulty = DifficultyLevel.from_value(body.get("diff"))
        topic = self.app().file_manager.load_by_id(topic_id)
        if topic is None:
            return self._send_json({"error": "Topic not found."}, 404)
        if not topic.modify_question(question_id, prompt, option_a, option_b,
                                     correct, difficulty):
            return self._send_json({"error": "Question not found."}, 404)
        self.app().file_manager.save_topic_to_file(topic)
        self._send_json(self._topics_payload())

    def _api_delete_question(self, topic_id: str, question_id: str) -> None:
        topic = self.app().file_manager.load_by_id(topic_id)
        if topic is None:
            return self._send_json({"error": "Topic not found."}, 404)
        if not topic.delete_question(question_id):
            return self._send_json({"error": "Question not found."}, 404)
        self.app().file_manager.save_topic_to_file(topic)
        self._send_json(self._topics_payload())

    def _api_delete_topic(self, topic_id: str) -> None:
        if not self.app().file_manager.delete_by_id(topic_id):
            return self._send_json({"error": "Topic not found."}, 404)
        self._send_json(self._topics_payload())

    def _api_save_account(self, body: dict) -> None:
        name = (body.get("display_name") or "").strip()
        if not name:
            return self._send_json({"error": "Display name cannot be empty."}, 400)
        name = (name[:40]).strip()
        user = self._session()["user"]
        user.set_username(name)
        self._pending_cookies.append("display_name=" + quote(name) + "; Path=/")
        self._send_json({"username": name})

    def _api_submit_quiz(self, body: dict) -> None:
        topic_id = body.get("topic_id")
        difficulty = DifficultyLevel.from_value(body.get("difficulty"))
        answers = body.get("answers") or []
        topic = self.app().file_manager.load_by_id(topic_id)
        if topic is None:
            return self._send_json({"error": "Topic not found."}, 404)
        generator = QuizGenerator(self.app().file_manager)
        quiz = generator.generate_quiz(topic, difficulty)
        for item in answers:
            question_id = item.get("question_id")
            selected = item.get("selected")
            if question_id is None or selected is None:
                continue
            try:
                quiz.submit_answer(question_id, int(selected))
            except (TypeError, ValueError):
                continue
        result = quiz.generate_result()
        self._send_json({
            "result": {
                "topic_name": result.get_topic_name(),
                "difficulty": result.get_difficulty().value,
                "score": result.get_score(),
                "total": len(quiz.get_questions()),
                "percentage": round(result.get_percentage(), 1),
            }
        })


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main() -> None:
    file_manager = TopicFileManager(STORAGE_DIRECTORY)
    server = QuizAppServer((HOST, PORT), RequestHandler, file_manager)
    print("=" * 62)
    print("  brAIndance - Quiz Management and Generation System")
    print(f"  Serving app at  http://{HOST}:{PORT}/")
    print("  Press Ctrl+C to stop.")
    print("=" * 62)
    if os.environ.get("QUIZ_NO_BROWSER") != "1":
        try:
            webbrowser.open(f"http://{HOST}:{PORT}/")
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()