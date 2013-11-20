CREATE TABLE "adm_custompermissions" (
    "id" integer NOT NULL PRIMARY KEY
);
CREATE TABLE "auth_group" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(80) NOT NULL UNIQUE
);
CREATE TABLE "auth_group_permissions" (
    "id" integer NOT NULL PRIMARY KEY,
    "group_id" integer NOT NULL,
    "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id"),
    UNIQUE ("group_id", "permission_id")
);
CREATE TABLE "auth_permission" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(50) NOT NULL,
    "content_type_id" integer NOT NULL,
    "codename" varchar(100) NOT NULL,
    UNIQUE ("content_type_id", "codename")
);
CREATE TABLE "auth_user" (
    "id" integer NOT NULL PRIMARY KEY,
    "username" varchar(30) NOT NULL UNIQUE,
    "first_name" varchar(30) NOT NULL,
    "last_name" varchar(30) NOT NULL,
    "email" varchar(75) NOT NULL,
    "password" varchar(128) NOT NULL,
    "is_staff" bool NOT NULL,
    "is_active" bool NOT NULL,
    "is_superuser" bool NOT NULL,
    "last_login" datetime NOT NULL,
    "date_joined" datetime NOT NULL
);
CREATE TABLE "auth_user_groups" (
    "id" integer NOT NULL PRIMARY KEY,
    "user_id" integer NOT NULL,
    "group_id" integer NOT NULL REFERENCES "auth_group" ("id"),
    UNIQUE ("user_id", "group_id")
);
CREATE TABLE "auth_user_user_permissions" (
    "id" integer NOT NULL PRIMARY KEY,
    "user_id" integer NOT NULL,
    "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id"),
    UNIQUE ("user_id", "permission_id")
);
CREATE TABLE "cerberos_failedaccessattempt" (
    "id" integer NOT NULL PRIMARY KEY,
    "created" datetime NOT NULL,
    "modified" datetime NOT NULL,
    "site_id" integer NOT NULL REFERENCES "django_site" ("id"),
    "ip_address" char(15),
    "user_agent" varchar(255) NOT NULL,
    "username" varchar(255) NOT NULL,
    "failed_logins" integer unsigned NOT NULL,
    "locked" bool NOT NULL,
    "expired" bool NOT NULL,
    "get_data" text NOT NULL,
    "post_data" text NOT NULL,
    "http_accept" text NOT NULL,
    "path_info" varchar(255) NOT NULL
);
CREATE TABLE "django_admin_log" (
    "id" integer NOT NULL PRIMARY KEY,
    "action_time" datetime NOT NULL,
    "user_id" integer NOT NULL REFERENCES "auth_user" ("id"),
    "content_type_id" integer REFERENCES "django_content_type" ("id"),
    "object_id" text,
    "object_repr" varchar(200) NOT NULL,
    "action_flag" smallint unsigned NOT NULL,
    "change_message" text NOT NULL
);
CREATE TABLE "django_content_type" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(100) NOT NULL,
    "app_label" varchar(100) NOT NULL,
    "model" varchar(100) NOT NULL,
    UNIQUE ("app_label", "model")
);
CREATE TABLE "django_session" (
    "session_key" varchar(40) NOT NULL PRIMARY KEY,
    "session_data" text NOT NULL,
    "expire_date" datetime NOT NULL
);
CREATE TABLE "django_site" (
    "id" integer NOT NULL PRIMARY KEY,
    "domain" varchar(100) NOT NULL,
    "name" varchar(50) NOT NULL
);
CREATE TABLE "missions_attachment" (
    "id" integer NOT NULL PRIMARY KEY,
    "attached_file" varchar(100),
    "attached_when" datetime NOT NULL,
    "attached_by_id" integer NOT NULL REFERENCES "organization_staff" ("id"),
    "safety_id" integer NOT NULL REFERENCES "missions_safety" ("id")
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
    "id" integer NOT NULL PRIMARY KEY,
    "created" date NOT NULL,
    "request_id" integer,
    "safety" text NOT NULL,
    "team_id" integer REFERENCES "organization_team" ("id"),
    "number" integer,
    "date" varchar(10),
    UNIQUE ("team_id", "date", "number")
);
CREATE TABLE "missions_vulnerability" (
    "id" integer NOT NULL PRIMARY KEY,
    "created" date NOT NULL,
    "number" integer NOT NULL,
    "date" date NOT NULL,
    "s1istatprov" varchar(4) NOT NULL,
    "s1istatcom" varchar(7) NOT NULL,
    "s1com" varchar(30) NOT NULL,
    "s2istatcens" varchar(30),
    "s2aggn" varchar(10),
    "s2edn" varchar(10),
    "s2viacorso" integer,
    "s2via" varchar(30),
    "s2civico" varchar(6),
    "s2accessi" integer,
    "s2fronti" integer,
    "s2catfoglio" varchar(10),
    "s2catalle" varchar(10),
    "s2catpart1" varchar(10),
    "s2cartfoglio" varchar(10),
    "s2cartagg" varchar(10),
    "s2cartedi" varchar(10),
    "s2zonapiano" bool NOT NULL,
    "s2pianoattuat" bool NOT NULL,
    "s2vincoli" bool NOT NULL,
    "s3sup" varchar(10),
    "s3supnpiani" varchar(5),
    "s3altpian" varchar(3),
    "s3altpianmedia" varchar(5),
    "s3altmax" varchar(5),
    "s3altmin" varchar(5),
    "s3largfronte" varchar(5),
    "s4unituso" integer,
    "s4stato" varchar(30),
    "s4condiz" integer,
    "s4prop" varchar(50),
    "s4conduz" integer,
    "s4residen" bool NOT NULL,
    "s4abitoccup" integer,
    "s4occupsuperperc" integer,
    "s4abitliber" integer,
    "s4libersuperperc" integer,
    "s4abitsalt" integer,
    "s4saltsuperperc" integer,
    "team_id" integer REFERENCES "organization_team" ("id")
);
CREATE TABLE "organization_abilitazione" (
    "id" integer NOT NULL PRIMARY KEY,
    "user_id" integer NOT NULL REFERENCES "organization_staff" ("id"),
    "activity" integer NOT NULL,
    "date" date NOT NULL,
    "last_training_date" date NOT NULL,
    "othercourses" text NOT NULL
);
CREATE TABLE "organization_agency" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(255) NOT NULL UNIQUE,
    "prov" varchar(255) NOT NULL,
    "short_name" varchar(255) NOT NULL
);
CREATE TABLE "organization_event" (
    "id" integer NOT NULL PRIMARY KEY,
    "date" date NOT NULL,
    "name" varchar(100) NOT NULL,
    "active" bool NOT NULL,
    "referente" varchar(100) NOT NULL,
    "referente2" varchar(100) NOT NULL,
    "cell_referente" varchar(20) NOT NULL,
    "cell_referente2" varchar(20) NOT NULL
);
CREATE TABLE "organization_role" (
    "id" integer NOT NULL PRIMARY KEY,
    "group_id" integer UNIQUE REFERENCES "auth_group" ("id"),
    "display_name" varchar(255) NOT NULL,
    "created" date NOT NULL
);
CREATE TABLE "organization_staff" (
    "id" integer NOT NULL PRIMARY KEY,
    "user_id" integer UNIQUE REFERENCES "auth_user" ("id"),
    "title" integer,
    "role" integer,
    "phone1" varchar(32) NOT NULL,
    "phone2" varchar(32) NOT NULL,
    "agency_id" integer
);
CREATE TABLE "organization_staff_abilitazioni" (
    "id" integer NOT NULL PRIMARY KEY,
    "staff_id" integer NOT NULL,
    "abilitazione_id" integer NOT NULL,
    UNIQUE ("staff_id", "abilitazione_id")
);
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
CREATE TABLE "organization_team_users" (
    "id" integer NOT NULL PRIMARY KEY,
    "team_id" integer NOT NULL,
    "staff_id" integer NOT NULL REFERENCES "organization_staff" ("id"),
    UNIQUE ("team_id", "staff_id")
);
CREATE TABLE "tastypie_apiaccess" (
    "id" integer NOT NULL PRIMARY KEY,
    "identifier" varchar(255) NOT NULL,
    "url" varchar(255) NOT NULL,
    "request_method" varchar(10) NOT NULL,
    "accessed" integer unsigned NOT NULL
);
CREATE TABLE "tastypie_apikey" (
    "id" integer NOT NULL PRIMARY KEY,
    "user_id" integer NOT NULL UNIQUE REFERENCES "auth_user" ("id"),
    "key" varchar(256) NOT NULL,
    "created" datetime NOT NULL
);
CREATE INDEX "auth_group_permissions_1e014c8f" ON "auth_group_permissions" ("permission_id");
CREATE INDEX "auth_group_permissions_bda51c3c" ON "auth_group_permissions" ("group_id");
CREATE INDEX "auth_permission_e4470c6e" ON "auth_permission" ("content_type_id");
CREATE INDEX "auth_user_groups_bda51c3c" ON "auth_user_groups" ("group_id");
CREATE INDEX "auth_user_groups_fbfc09f1" ON "auth_user_groups" ("user_id");
CREATE INDEX "auth_user_user_permissions_1e014c8f" ON "auth_user_user_permissions" ("permission_id");
CREATE INDEX "auth_user_user_permissions_fbfc09f1" ON "auth_user_user_permissions" ("user_id");
CREATE INDEX "cerberos_failedaccessattempt_4a0a4867" ON "cerberos_failedaccessattempt" ("ip_address");
CREATE INDEX "cerberos_failedaccessattempt_6223029" ON "cerberos_failedaccessattempt" ("site_id");
CREATE INDEX "cerberos_failedaccessattempt_ae187eb1" ON "cerberos_failedaccessattempt" ("locked");
CREATE INDEX "cerberos_failedaccessattempt_f774835d" ON "cerberos_failedaccessattempt" ("username");
CREATE INDEX "django_admin_log_e4470c6e" ON "django_admin_log" ("content_type_id");
CREATE INDEX "django_admin_log_fbfc09f1" ON "django_admin_log" ("user_id");
CREATE INDEX "django_session_c25c2c28" ON "django_session" ("expire_date");
CREATE INDEX "missions_attachment_401bf584" ON "missions_attachment" ("safety_id");
CREATE INDEX "missions_attachment_97f10893" ON "missions_attachment" ("attached_by_id");
CREATE INDEX "missions_request_e9b82f95" ON "missions_request" ("event_id");
CREATE INDEX "missions_request_fcf8ac47" ON "missions_request" ("team_id");
CREATE INDEX "missions_safety_792812e8" ON "missions_safety" ("request_id");
CREATE INDEX "missions_safety_fcf8ac47" ON "missions_safety" ("team_id");
CREATE INDEX "missions_vulnerability_fcf8ac47" ON "missions_vulnerability" ("team_id");
CREATE INDEX "organization_abilitazione_fbfc09f1" ON "organization_abilitazione" ("user_id");
CREATE INDEX "organization_staff_abilitazioni_3aac915" ON "organization_staff_abilitazioni" ("abilitazione_id");
CREATE INDEX "organization_staff_abilitazioni_a2044c77" ON "organization_staff_abilitazioni" ("staff_id");
CREATE INDEX "organization_staff_b162e9d" ON "organization_staff" ("agency_id");
CREATE INDEX "organization_team_e9b82f95" ON "organization_team" ("event_id");
CREATE INDEX "organization_team_users_a2044c77" ON "organization_team_users" ("staff_id");
CREATE INDEX "organization_team_users_fcf8ac47" ON "organization_team_users" ("team_id");