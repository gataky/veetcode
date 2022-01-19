import time
import json
import os
import re
import sqlite3
import string
import textwrap
from collections import defaultdict

import browser_cookie3
import pynvim
import requests
from requests import Session, adapters
from tabulate import tabulate

LC_BASE = "https://leetcode.com"


def ErrorHandler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as err:
            return None
    return wrapper


class CookiesNotFoundException(Exception):
    def __init__(self, browser):
        super().__init__(f"Cookies not found, please login through {browser}")


class Auth:
    def __init__(self, session, browser="chrome"):
        cookies = getattr(browser_cookie3, browser)(domain_name=".leetcode.com")
        if cookies is None:
            raise CookiesNotFoundException(browser)

        self.session = session
        for cookie in cookies:
            if cookie.name == "LEETCODE_SESSION":
                self.session.cookies.set_cookie(cookie)

    def __call__(self, request):
        headers = {
            "Origin": LC_BASE,
            "Referer": LC_BASE,
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": self.session.cookies.get("csrftoken", ""),
        }
        headers.update(request.headers)
        request.headers.update(headers)
        return request


class LeetCode(Session):
    def __init__(self, *args, browser="chrome", **kwargs):
        super().__init__()

        self.auth = Auth(self, browser)

        adapter = adapters.HTTPAdapter()
        self.mount("https://", adapter)
        self.mount("http://", adapter)

    def get_problems(self, category="algorithms"):
        url = LC_BASE + f"/api/problems/{category}"
        return Problems(self.get(url).json())

    def get_tags(self, raw=False):
        url = f"{LC_BASE}/problems/api/tags/"
        resp = self.get(url).json()
        if raw:
            return resp
        c = t = None
        for category, tags in resp.items():
            if category == "companies":
                c = CompanyTags(tags)
            elif category == "topics":
                t = TopicTags(tags)
        return (c, t)

    def get_problem(self, slug):
        query = {
            "operationName": "questionData",
            "variables": {"titleSlug": slug},
            "query": "query questionData($titleSlug: String\u0021) {question(titleSlug: $titleSlug) { questionId questionFrontendId boundTopicId title titleSlug content translatedTitle translatedContent isPaidOnly difficulty likes dislikes isLiked similarQuestions exampleTestcases contributors { username profileUrl avatarUrl __typename } topicTags { name slug translatedName __typename } codeSnippets { lang langSlug code __typename } stats hints solution { id canSeeDetail paidOnly hasVideoSolution paidOnlyVideo __typename } status sampleTestCase metaData judgerAvailable judgeType mysqlSchemas enableRunCode enableTestMode enableDebugger challengeQuestion { id date incompleteChallengeCount streakCount type __typename } __typename }}",
        }
        url = LC_BASE + "/graphql"
        resp = self.post(url, json=query)
        return resp

    def submit_problem(self, id, slug, code):
        url = LC_BASE + f"/problems/{slug}/submit/"

        data = {
            'question_id': id,
            'lang': 'python3',
            'typed_code': code
        }

        r = self.get(LC_BASE)
        csrf = r.headers['Set-Cookie'].split(';')[0].split('=')[1]

        resp = self.post(url, json=data, headers={'csrftoken': csrf})

        sid = resp.json().get('submission_id')
        url = LC_BASE + f"/submissions/detail/{sid}/check/"
        for x in range(5):
            resp = self.get(url)
            if resp.json().get('state') == 'SUCCESS':
                return resp
            time.sleep(2)


class Base(list):
    def __init__(self):
        super().__init__()

    def filter(self, condition):
        return list(filter(condition, self))


class Problems(Base):
    def __init__(self, problems):
        super().__init__()
        for problem in problems["stat_status_pairs"]:
            self.append(Problem(**problem))
        self.sort(key=lambda p: p.id)

    def apply_tags(self, tags):

        pm = {p.id: p for p in self}

        for tag in tags:
            for i, pid in enumerate(tag.questions):
                p = pm.get(pid)
                if p:
                    p.add_tag(tag)
                    tag.questions[i] = p

    def to_rows(self):
        for p in self:
            yield p.row()


class Problem:
    status_map = {
        None: 1,
        "notac": 2,
        "ac": 3,
    }

    def __init__(self, stat, status, difficulty, paid_only, frequency, **kwargs):
        self.id = stat.get("question_id")
        self.slug = stat.get("question__title_slug")
        if self.slug is None:
            self.slug = self._parse_title(stat.get("question__title"))

        self.difficulty_id = difficulty["level"]
        self.status_id = self.status_map.get(status)

        self.paid = paid_only
        self.frequency = frequency

        self.stat = stat

        self.tags = []

    def __repr__(self):
        return f"""{self.status_id} {self.difficulty_id} {self.id:04}: {self.stat.get("question__title")}"""

    def _parse_title(self, title):
        clean = re.sub("\s", "-", title)
        clean = re.sub("[^a-zA-Z0-9_-]", "", clean)
        return clean.lower()

    def row(self):
        return (
            self.id,
            self.stat.get("question__title"),
            self.slug,
            self.difficulty_id,
            self.status_id,
            self.paid,
            self.frequency,
        )


class Tags(Base):
    def __init__(self, tags):
        super().__init__()
        for i, tag in enumerate(tags, start=1):
            self.append(Tag(id=i, **tag))

    def to_rows(self):
        for t in self:
            yield t.row()


class CompanyTags(Tags):
    pass


class TopicTags(Tags):
    pass


class Tag:
    def __init__(self, id, name, slug, questions, **kwargs):
        self.id = id
        self.name = name
        self.slug = slug
        self.questions = questions

    def __repr__(self):
        return f"{self.slug}"

    def row(self):
        return (self.id, self.name, self.slug)


sort_symbol = {
    0: "▲",
    1: "‒",
    2: "▼",
}

symbols = {1: "-", 2: "☓", 3: "✓"}

levels = {1: "Easy", 2: "Medium", 3: "Hard"}


con = None
cur = None
cwd = "~/"


def set_script_directory(path):
    global cwd, cur, con
    cwd = path
    con = sqlite3.connect(os.path.join(cwd, "foo.db"))
    cur = con.cursor()


problem_dir = "~/.local/share/veetcode"


def set_problem_directory(path):
    path = os.path.expanduser(path)
    if os.path.exists(path) == False:
        os.mkdir(path)
    global problem_dir
    problem_dir = path


@ErrorHandler
def initialize_db():
    lc = LeetCode()
    companies, tags = lc.get_tags()
    problems = lc.get_problems()

    NOOP = "ON CONFLICT DO NOTHING"

    # =================================================================================
    query = f"""
        INSERT INTO problems
            (id, name, slug, difficulty_id, status_id, paid, frequency)
        VALUES
            (?, ?, ?, ?, ?, ?, ?) {NOOP}
    """
    data = [p.row() for p in problems]
    cur.executemany(query, data)

    # =================================================================================
    query = f"INSERT INTO companies (id, name, slug) VALUES (?, ?, ?) {NOOP}"
    data = [t.row() for t in companies]
    cur.executemany(query, data)

    # =================================================================================
    query = f"INSERT INTO tags (id, name, slug) VALUES (?, ?, ?) {NOOP}"
    data = [t.row() for t in tags]
    cur.executemany(query, data)

    # =================================================================================
    query = f"INSERT INTO problem_company (problem_id, company_id) VALUES (?, ?) {NOOP}"
    data = [(p, c.id) for c in companies for p in c.questions]
    cur.executemany(query, data)

    # =================================================================================
    query = f"INSERT INTO problem_tag (problem_id, tag_id) VALUES (?, ?) {NOOP}"
    data = [(p, t.id) for t in tags for p in t.questions]
    cur.executemany(query, data)

    con.commit()
    con.close()


@ErrorHandler
def get_tags(tag_type, tag=""):

    tag = tag.strip("+").lower().strip()
    tag_type = tag_type.lower()

    if tag:
        query = f"UPDATE {tag_type} SET active = not active WHERE slug = ?"
        cur.execute(query, (tag,))
        con.commit()

    query = f"SELECT id, slug, active FROM {tag_type} ORDER BY slug"

    resp = cur.execute(query)
    rows = resp.fetchall()

    tag_groups = defaultdict(list)
    if tag_type in {"difficulty", "status"}:
        rows.sort(key=lambda x: x[0])
    for row in rows:
        (id, name, active) = row
        if active:
            prefix = "+"
        else:
            prefix = " "

        if tag_type in {"difficulty", "status"}:
            tag_groups[" "].append(prefix + name)
        else:
            tag_groups[name[0]].append(prefix + name)

    tags = []
    for letter in string.ascii_lowercase + " ":
        group = tag_groups.get(letter)
        if not group:
            continue
        if group:
            tags.extend(
                textwrap.wrap(
                    " ".join(group),
                    width=86,
                    break_long_words=False,
                    break_on_hyphens=False,
                    initial_indent=" " * 7,
                    subsequent_indent=" " * 8,
                )
            )
    return tags


@ErrorHandler
def get_problems(orders=None):

    order_by = []
    column = ["p.difficulty_id", "p.status_id", "p.id", "p.name", "p.frequency"]
    for i, order in enumerate(orders):
        if order == 0:
            by = "ASC"
        elif order == 1:
            by = None
        else:
            by = "DESC"

        if by is not None:
            order_by.append(f"{column[i]} {by}")

    order_by = ",\n".join(order_by)
    if order_by:
        order_by = "ORDER BY " + order_by

    filters = {"companies": None, "tags": None, "difficulty": None, "status": None}

    for filter in filters.keys():
        query = "SELECT id FROM {table} WHERE active IS TRUE".format(table=filter)
        resp = cur.execute(query)
        rows = resp.fetchall()
        data = ", ".join([str(row[0]) for row in rows])
        if data:
            if filter == "tags":
                query = f"JOIN tags       ON problem_tag.tag_id         IN ({data})"
            elif filter == "companies":
                query = f"JOIN companies  ON problem_company.company_id IN ({data})"
            elif filter == "difficulty":
                query = f"JOIN difficulty ON p.difficulty_id            IN ({data})"
            else:
                query = f"JOIN status     ON p.status_id                IN ({data})"
            filters[filter] = query
        else:
            filters[filter] = ""

    query = """
        SELECT
            DISTINCT p.difficulty_id, p.status_id, p.id, p.name
        FROM problems AS p
            JOIN problem_tag ON p.id = problem_tag.problem_id
            {tags}
            JOIN problem_company ON p.id = problem_company.problem_id
            {companies}
            {status}
            {difficulty}
            {order_by}
    """.format(
        order_by=order_by, **filters
    )

    resp = cur.execute(query)

    problems = []
    for problem in resp.fetchall():
        problem = list(problem)
        problem[0] = levels[problem[0]]
        problem[1] = symbols[problem[1]]
        problems.append(problem)
    return problems


def setup_filters():
    output = ["Filters"]
    for tag_type in ["Companies", "Tags", "Difficulty", "Status"]:
        output.append(f"    {tag_type}")
        output.extend(get_tags(tag_type))
    output.append("")
    return output


def setup_problems():
    query = "SELECT * FROM ordering"
    resp = cur.execute(query)
    ordering = resp.fetchone()

    ordering_symbols = [sort_symbol[order] for order in ordering]
    headers = ["Level", "Status", "ID ", "Title", "Frequency"]
    headers = [s + h for s, h in zip(ordering_symbols, headers)]

    problems = get_problems(ordering)
    table = tabulate(
        problems,
        headers,
        tablefmt="fancy_outline",
        as_array=True,
        colalign=("center", "center"),
    )
    output = ["Problems"]
    output.extend(table)
    return output


def toggle_order(header):
    query = f"UPDATE ordering SET {header} = ({header} + 1) % 3"
    cur.execute(query)
    con.commit()


@ErrorHandler
def get_problem(id, get_for="display"):

    dir = os.path.join(problem_dir, str(id))
    if not os.path.exists(dir):
        os.mkdir(dir)
    elif os.path.exists(dir) and get_for == 'display':
        resp = {}
        with open(os.path.join(dir, 'code.py'), 'rb') as f:
            resp['snippet'] = f.read().decode('utf-8')
        with open(os.path.join(dir, 'prompt.md'), 'rb') as f:
            resp['prompt'] = f.read().decode('utf-8')
        with open(os.path.join(dir, 'test.py'), 'rb') as f:
            resp['test'] = f.read().decode('utf-8')
        return resp

    query = "SELECT slug FROM problems WHERE id = ?"
    resp = cur.execute(query, (id,))
    slug = resp.fetchone()[0]

    lc = LeetCode()
    resp = lc.get_problem(slug)

    data = resp.json()
    question = data["data"]["question"]
    prompt = question["content"].split("\n")

    snippets = question["codeSnippets"]
    snippet = list(filter(lambda x: x["langSlug"] == "python3", snippets))[0][
        "code"
    ].split("\n")

    if get_for == "display":
        return {"snippet": snippet, "prompt": prompt}
    else:
        for fn, data in [("code.py", snippet), ("prompt.md", prompt), ("test.py", "")]:
            fp = os.path.join(dir, fn)
            if os.path.exists(fp):
                continue
            with open(fp, "wb") as f:
                if isinstance(data, (list, tuple)):
                    f.write("\n".join(data).encode("utf-8"))
                elif isinstance(data, str):
                    f.write(data.encode("utf-8"))
                else:
                    f.write(data)


def set_problem_downloaded(id):
    query = "UPDATE problems SET downloaded = TRUE WHERE id = ?"
    cur.execute(query, (id,))
    con.commit()


@ErrorHandler
def submit_problem(id):
    query = "SELECT slug FROM problems WHERE id = ?"
    resp = cur.execute(query, (id,))
    slug = resp.fetchone()[0]

    lc = LeetCode()

    with open(os.path.join(problem_dir, str(id), 'code.py'), 'rb') as f:
        code = f.read().decode('utf-8')
    resp = lc.submit_problem(id, slug, code)
    return resp.json().get('status_msg')



if __name__ == "__main__":
    set_script_directory(".")
    set_problem_directory(problem_dir)
