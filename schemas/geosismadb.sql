SELECT InitSpatialMetadata();

-------------------------------------------------------------------

CREATE TABLE istat_regioni
(
  id_istat text  NOT NULL,
  toponimo text  NOT NULL,
  CONSTRAINT istat_regioni_pkey PRIMARY KEY (id_istat)
);

-------------------------------------------------------------------

CREATE TABLE istat_province
(
  id_istat text  NOT NULL,
  toponimo text  NOT NULL,
  idregione text  NOT NULL,
  sigla text  NOT NULL,
  CONSTRAINT istat_province_pkey PRIMARY KEY (id_istat),
  CONSTRAINT istat_province_idregione_fkey FOREIGN KEY (idregione)
      REFERENCES istat_regioni (id_istat) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION,
  CONSTRAINT istat_province_sigla_key UNIQUE (sigla)
);

-------------------------------------------------------------------

CREATE TABLE istat_comuni
(
  id_istat text NOT NULL,
  toponimo text  NOT NULL,
  idprovincia text NOT NULL,
  CONSTRAINT istat_comuni_idprovincia_fkey FOREIGN KEY (idprovincia)
      REFERENCES istat_province (id_istat) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION,
  CONSTRAINT istat_comuni_key UNIQUE (idprovincia, id_istat)
);

-------------------------------------------------------------------

CREATE TABLE codici_belfiore
(
  id text NOT NULL,
  id_regione text,
  id_provincia text,
  id_comune text,
  toponimo text ,
  CONSTRAINT codici_belfiore_pkey PRIMARY KEY (id)
);

-------------------------------------------------------------------

CREATE TABLE istat_loc_tipi
(
  id integer NOT NULL,
  tipo text NOT NULL,
  CONSTRAINT istat_loc_tipi_pkey PRIMARY KEY (id)
);
-------------------------------------------------------------------

CREATE TABLE istat_loc
(
  id integer NOT NULL,
  denom_loc text NOT NULL,
  centro_cl boolean NOT NULL,
  popres integer NOT NULL,
  maschi integer NOT NULL,
  famiglie integer NOT NULL,
  alloggi integer NOT NULL,
  edifici integer NOT NULL,
  cod_pro text NOT NULL,
  cod_com text NOT NULL,
  cod_loc text NOT NULL,
  loc2001 text,
  altitudine double precision,
  denom_pro text,
  denom_com text,
  sigla_prov text,
  tipo_loc integer NOT NULL,
  sez2001 text NOT NULL,
  CONSTRAINT istat_loc_pkey PRIMARY KEY (id),
  CONSTRAINT istat_loc_tipo_loc_fkey FOREIGN KEY (tipo_loc)
      REFERENCES istat_loc_tipi (id) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION
);
SELECT AddGeometryColumn( 'istat_loc', 'the_geom', 32632, 'MULTIPOLYGON', 'XY');
SELECT CreateSpatialIndex('istat_loc', 'the_geom');
  
-------------------------------------------------------------------

CREATE TABLE catasto_2010
(
	gid integer NOT NULL,
	valenza text,
	esterconf text,
	codbo text,
	tipo text,
	dim real,
	ang real,
	posx real,
	posy real,
	pintx real,
	pinty real,
	sup real,
	belfiore text,
	zona_cens text,
	foglio text,
	allegato text,
	sviluppo text,
	fog_ann text,
	orig text,
	label text ,
	CONSTRAINT catasto_2010_pkey PRIMARY KEY (gid)
);
SELECT AddGeometryColumn( 'catasto_2010', 'the_geom', 32632, 'MULTIPOLYGON', 'XY');
SELECT CreateSpatialIndex('catasto_2010', 'the_geom');
