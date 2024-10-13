DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS zettels;
DROP TABLE IF EXISTS tags_zettels;

CREATE TABLE tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tagname TEXT NOT NULL,
  colour TEXT NOT NULL DEFAULT "#FFFFFF"
);

CREATE TABLE zettels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  body TEXT NOT NULL,
  modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tags_zettels (
  tagid INTEGER NOT NULL,
  zettelid INTEGER NOT NULL,
  FOREIGN KEY (tagid) REFERENCES tags(id),
  FOREIGN KEY (zettelid) REFERENCES zettels(id)
);


INSERT INTO zettels (body) VALUES ('First zettel to be entered');
INSERT INTO zettels (body) VALUES ('Second zettel');
INSERT INTO tags (tagname) VALUES ('python');
INSERT INTO tags (tagname) VALUES ('flask');
INSERT INTO tags_zettels (tagid, zettelid) VALUES (1, 2);
INSERT INTO tags_zettels (tagid, zettelid) VALUES (2, 1);
