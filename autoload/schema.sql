PRAGMA foreign_keys = ON;

CREATE TABLE difficulty (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL,
    active BOOLEAN DEFAULT FALSE
);
-- IDs match with the IDs leetcode uses for these values.
INSERT INTO difficulty (slug) values ('easy'), ('medium'), ('hard');


CREATE TABLE status (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL,
    symbol TEXT NOT NULL,
    active BOOLEAN DEFAULT FALSE
);
-- LeetCode codes                          null           notac              ac
-- IDs                                       1              2                 3
INSERT INTO status (slug, symbol) values ('todo', '-'), ('working', '☓'), ('done', '✓');


CREATE TABLE problems (
    id INTEGER NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT,
    difficulty_id INTEGER NOT NULL,
    status_id INTEGER NOT NULL,
    paid BOOLEAN DEFAULT FALSE,
    frequency REAL,
    submitted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (difficulty_id) REFERENCES difficulty (id),
    FOREIGN KEY (status_id)     REFERENCES status     (id)
);
CREATE UNIQUE INDEX problems_slug_uidx ON problems (slug);


CREATE TABLE companies (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    active BOOLEAN DEFAULT FALSE
);
CREATE UNIQUE INDEX companies_slug_uidx ON companies (slug);


CREATE TABLE tags (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    active BOOLEAN DEFAULT FALSE
);
CREATE UNIQUE INDEX tags_slug_uidx ON tags (slug);


CREATE TABLE problem_tag (
    problem_id INTEGER,
    tag_id INTEGER,
    FOREIGN KEY (problem_id) REFERENCES problems (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id)     REFERENCES tags     (id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX problem_tag_uidx ON problem_tag (problem_id, tag_id);
CREATE        INDEX tag_problem_idx  ON problem_tag (tag_id, problem_id);


CREATE TABLE problem_company (
    problem_id INTEGER,
    company_id INTEGER,
    FOREIGN KEY (problem_id) REFERENCES problems  (id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX problem_company_uidx ON problem_company (problem_id, company_id);
CREATE        INDEX company_problem_idx  ON problem_company (company_id, problem_id);


CREATE TABLE attempts (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER NOT NULL,
    status_id TEXT NOT NULL,
    submitted TEXT NOT NULL DEFAULT (DATETIME('now'))
);


CREATE TABLE ordering (
    level     INTEGER DEFAULT FALSE,
    status    INTEGER DEFAULT FALSE,
    id        INTEGER DEFAULT FALSE,
    title     INTEGER DEFAULT FALSE,
    frequency INTEGER DEFAULT FALSE
);
INSERT INTO ordering VALUES (FALSE, FALSE, FALSE, FALSE, FALSE);
