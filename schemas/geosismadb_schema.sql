SELECT InitSpatialMetadata();

CREATE TABLE "missions_attachment" (
    "id" integer NOT NULL PRIMARY KEY,
    "attached_file" varchar(100),
    "attached_when" datetime NOT NULL,
    "attached_by_id" integer NOT NULL REFERENCES "organization_staff" ("id"),
    "safety_id" integer NOT NULL REFERENCES "missions_safety" ("local_id")
);

CREATE TABLE "missions_request" (
    "id" integer NOT NULL PRIMARY KEY,
    "number" integer NOT NULL,
    "s1name" varchar(100) NOT NULL,
    "s1prov" varchar(100) NOT NULL,
    "s1com" varchar(100) NOT NULL,
    "s1loc" varchar(100) NOT NULL,
    "s1via" varchar(100) NOT NULL,
    "s1civico" varchar(100) NOT NULL,
    "s1catfoglio" varchar(100) NOT NULL,
    "s1catpart1" varchar(100) NOT NULL,
    "created" date NOT NULL,
    "team_id" integer REFERENCES "organization_team" ("id"),
    "event_id" integer NOT NULL REFERENCES "organization_event" ("id")
);

CREATE TABLE "missions_safety" (
    "local_id" integer NOT NULL PRIMARY KEY,
    "id" integer NOT NULL,
    "created" date NOT NULL,
    "request_id" integer,
    "safety" text NOT NULL,
    "team_id" integer REFERENCES "organization_team" ("id"),
    "number" integer,
    "date" varchar(10),
    "uploaded" integer,
    "gid_catasto" integer,
    UNIQUE ("team_id", "date", "number")
);
SELECT AddGeometryColumn( 'missions_safety', 'the_geom', 3003, 'MULTIPOLYGON', 'XY');
SELECT CreateSpatialIndex('missions_safety', 'the_geom');

CREATE TABLE "organization_team" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" integer NOT NULL,
    "created" date NOT NULL,
    "activity" integer NOT NULL,
    "date_start" date NOT NULL,
    "date_end" date NOT NULL,
    "event_id" integer REFERENCES "organization_event" ("id"),
    UNIQUE ("event_id", "name")
);

CREATE INDEX "missions_attachment_401bf584" ON "missions_attachment" ("safety_id");
CREATE INDEX "missions_attachment_97f10893" ON "missions_attachment" ("attached_by_id");
CREATE INDEX "missions_request_e9b82f95" ON "missions_request" ("event_id");
CREATE INDEX "missions_request_fcf8ac47" ON "missions_request" ("team_id");
CREATE INDEX "missions_safety_792812e8" ON "missions_safety" ("request_id");
CREATE INDEX "missions_safety_fcf8ac47" ON "missions_safety" ("team_id");
CREATE INDEX "organization_team_e9b82f95" ON "organization_team" ("event_id");
