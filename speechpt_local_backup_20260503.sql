--
-- PostgreSQL database dump
--

\restrict bgOJgfYruMqxmDy25jbdHDZchgZiWW46I5rBgvuKjzgzIOG2hbRJPBwZmAZ4tlH

-- Dumped from database version 18.3 (Homebrew)
-- Dumped by pg_dump version 18.3 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: analyses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.analyses (
    analysis_id uuid NOT NULL,
    note_id uuid NOT NULL,
    user_id uuid NOT NULL,
    document_upload_id uuid NOT NULL,
    audio_upload_id uuid NOT NULL,
    pipeline_version character varying(50) NOT NULL,
    model_version_ce character varying(100),
    model_version_ae character varying(100),
    status character varying(20) NOT NULL,
    progress integer NOT NULL,
    stage character varying(20) NOT NULL,
    trigger_type character varying(20),
    worker_id character varying(100),
    error_code character varying(50),
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    CONSTRAINT ck_analysis_progress_range CHECK (((progress >= 0) AND (progress <= 100)))
);


--
-- Name: notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notes (
    note_id uuid NOT NULL,
    user_id uuid NOT NULL,
    title character varying(200) NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone
);


--
-- Name: uploads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.uploads (
    upload_id uuid NOT NULL,
    user_id uuid NOT NULL,
    note_id uuid,
    kind character varying(20) NOT NULL,
    storage character varying(20) NOT NULL,
    bucket character varying(200) NOT NULL,
    object_key character varying(500) NOT NULL,
    original_filename character varying(255) NOT NULL,
    url character varying(1000),
    content_type character varying(100) NOT NULL,
    size_bytes bigint NOT NULL,
    checksum character varying(128),
    status character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    user_id uuid NOT NULL,
    email character varying(100) NOT NULL,
    password_hash character varying(255),
    name character varying(100) NOT NULL,
    provider character varying(20) NOT NULL,
    provider_id character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Data for Name: analyses; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.analyses (analysis_id, note_id, user_id, document_upload_id, audio_upload_id, pipeline_version, model_version_ce, model_version_ae, status, progress, stage, trigger_type, worker_id, error_code, error_message, created_at, started_at, finished_at) FROM stdin;
be3b8fc6-b61a-4dfa-b09d-0a8ba60bfeda	ab9dccb5-d7bb-443b-8be2-be4134867511	11111111-1111-1111-1111-111111111111	fabafc73-5d4d-4fc9-99bc-8c966d6f09b4	22634a05-7014-4b51-a981-98754c20cce1	v0.1	ce-v0.1	ae-v0.1	queued	0	ingest	manual	\N	\N	\N	2026-03-14 20:46:39.364136+09	\N	\N
80d755e8-0d34-4ddd-97d4-7bc0d1f86387	f1428c4a-f827-42bd-8a75-a878dfebcf48	11111111-1111-1111-1111-111111111111	c4dad3f6-29ce-4fb9-abcf-b6752873fc07	c96633c3-e9b4-4e77-bea6-7bbdcd868fd1	string	string	string	done	0	ingest	manual	\N	\N	\N	2026-04-07 16:25:23.77753+09	\N	\N
099f63a4-7a31-4a9c-8ac6-a2690b887720	f1428c4a-f827-42bd-8a75-a878dfebcf48	11111111-1111-1111-1111-111111111111	1216e6a4-e7e9-4bff-86c2-5c98eed49853	554682d7-5d00-4a48-97a0-b42487c79579	v0.1	ce-v0.1	ae-v0.1	queued	0	ingest	manual	\N	\N	\N	2026-04-07 22:35:42.654513+09	\N	\N
f3d14c3c-2f98-41f8-9aff-3eab1f6a55c1	db79ee91-4116-4309-8267-b53ee3066151	11111111-1111-1111-1111-111111111111	c5770cba-f58e-4829-b6bb-c97cd839f768	890cdb60-418f-43b6-a823-efa3a8167c9e	v0.1	ce-v0.1	ae-v0.1	queued	0	ingest	manual	\N	\N	\N	2026-04-07 22:36:01.454685+09	\N	\N
c836d018-83d9-4d06-9302-77edc34c92b8	ab9dccb5-d7bb-443b-8be2-be4134867511	11111111-1111-1111-1111-111111111111	b7145eab-541a-4687-a237-ab571e903df3	7755bee0-1134-4125-a0e6-d27d8c2d2d86	v0.1	ce-v0.1	ae-v0.1	queued	0	ingest	manual	\N	\N	\N	2026-04-08 13:40:39.063591+09	\N	\N
781a6da2-454b-4660-b524-cf47e3efe163	ab9dccb5-d7bb-443b-8be2-be4134867511	11111111-1111-1111-1111-111111111111	f9f3cccb-97d5-4a63-a4fd-e8f60d9175e4	d92b7868-c3cb-41bc-9816-47da2900d0f6	v0.1	ce-v0.1	ae-v0.1	queued	0	ingest	manual	\N	\N	\N	2026-04-08 13:42:11.756785+09	\N	\N
0af5af38-92c4-4dd6-8948-b34b935e1417	ab9dccb5-d7bb-443b-8be2-be4134867511	11111111-1111-1111-1111-111111111111	3ace8511-6ff1-469d-87e6-5ea75c68416c	f0c86e61-4300-4af0-8c85-15c64a2bfa93	v0.1	ce-v0.1	ae-v0.1	queued	0	ingest	manual	\N	\N	\N	2026-04-08 13:50:00.064849+09	\N	\N
3c92e127-300e-4af3-969e-2e334bbdf0a6	ab9dccb5-d7bb-443b-8be2-be4134867511	11111111-1111-1111-1111-111111111111	407cec62-32a4-4ce1-a166-f38b9c870c16	ec2d94a0-0a64-4867-a46d-c342c0cdc833	v0.1	ce-v0.1	ae-v0.1	queued	0	ingest	manual	\N	\N	\N	2026-04-08 13:53:15.263027+09	\N	\N
5bfdfed5-f985-49ac-b32d-74f6914693ca	ab9dccb5-d7bb-443b-8be2-be4134867511	11111111-1111-1111-1111-111111111111	e0ed265d-70dd-4d74-aef4-332be89cf600	f57f99b7-ba5a-49c2-bbf6-e29d9a27a9a9	v0.1	ce-v0.1	ae-v0.1	queued	0	ingest	manual	\N	\N	\N	2026-04-08 13:55:44.653709+09	\N	\N
33b5f785-9a37-450d-989d-6d5d955c90e7	ab9dccb5-d7bb-443b-8be2-be4134867511	11111111-1111-1111-1111-111111111111	d9834239-e834-473d-9ff9-922286d3acd7	b247bb1a-ea0b-4e4f-b000-46688487eabd	v0.1	ce-v0.1	ae-v0.1	done	100	finished	manual	\N	\N	\N	2026-04-08 14:02:54.121279+09	2026-04-08 14:02:54.121279+09	2026-04-08 14:02:54.12734+09
51c64edd-830b-45d4-92d6-bbcf03046a2c	f1428c4a-f827-42bd-8a75-a878dfebcf48	11111111-1111-1111-1111-111111111111	9c4cccc7-3b22-4daf-b88d-b42a7d625183	25ac509b-2b20-48bc-8207-1cde8b54bd9e	v0.1	ce-v0.1	ae-v0.1	done	100	finished	manual	\N	\N	\N	2026-04-08 14:18:42.963277+09	2026-04-08 14:18:42.963277+09	2026-04-08 14:18:42.986369+09
e53fb27a-529e-4dca-ace1-2989fffec4fc	f1428c4a-f827-42bd-8a75-a878dfebcf48	11111111-1111-1111-1111-111111111111	b46edb72-4be5-4f57-98f8-98d3b1bd2a9c	9a6f3d2c-be38-412e-a193-d3b2daaa8a32	v0.1	ce-v0.1	ae-v0.1	done	100	finished	manual	\N	\N	\N	2026-04-08 14:22:33.423978+09	2026-04-08 14:22:33.423978+09	2026-04-08 14:22:33.427743+09
02f5cbf8-a559-43b3-b706-5f7be9db27f5	f1428c4a-f827-42bd-8a75-a878dfebcf48	11111111-1111-1111-1111-111111111111	ec436027-9a6a-440d-ba85-83be2185df88	5c0bf709-b46c-4be0-a8f6-9b46032437f0	v0.1	ce-v0.1	ae-v0.1	done	100	finished	manual	\N	\N	\N	2026-04-08 14:26:49.149659+09	2026-04-08 14:26:49.149659+09	2026-04-08 14:26:49.153035+09
422cfeb1-817a-409c-9e5f-33bed2e0a1b5	db79ee91-4116-4309-8267-b53ee3066151	11111111-1111-1111-1111-111111111111	23f8b098-248e-4e31-92fc-6d3cb6400427	ceccd05d-a10c-4eb5-aa7e-e406c403ad93	v0.1	ce-v0.1	ae-v0.1	done	100	finished	manual	\N	\N	\N	2026-04-08 18:42:30.370766+09	2026-04-08 18:42:30.370766+09	2026-04-08 18:42:30.377558+09
8ce0761d-7f1d-4cd0-86b4-14b28401aad0	db79ee91-4116-4309-8267-b53ee3066151	11111111-1111-1111-1111-111111111111	f898cdbb-b384-42af-badc-3c19fffbc261	38e01823-0f92-41a8-88df-cb4f2f19a15e	v0.1	ce-v0.1	ae-v0.1	done	100	finished	manual	\N	\N	\N	2026-04-09 22:05:21.049631+09	2026-04-09 22:05:21.049631+09	2026-04-09 22:05:21.065787+09
83283d24-fc1c-4054-b5ce-fce2ceb3ca87	db79ee91-4116-4309-8267-b53ee3066151	11111111-1111-1111-1111-111111111111	8fe2338b-7f84-4204-b730-ffc303d2e2ea	9d9a27be-2091-4a65-afeb-1f41a3ef3cfd	v0.1	ce-v0.1	ae-v0.1	done	100	finished	manual	\N	\N	\N	2026-04-09 22:13:14.405392+09	2026-04-09 22:13:14.405392+09	2026-04-09 22:13:14.409098+09
35a686e1-2dd1-4df4-8400-b71961c09e99	db79ee91-4116-4309-8267-b53ee3066151	11111111-1111-1111-1111-111111111111	c374b878-00e1-41b1-8e1e-a7e942d21660	7ddee677-4d68-4ccb-bf03-c3d8cf562661	v0.1	ce-v0.1	ae-v0.1	done	100	finished	manual	\N	\N	\N	2026-04-09 23:00:22.254712+09	2026-04-09 23:00:22.254712+09	2026-04-09 23:00:22.258791+09
4e31e80b-544a-4053-81b5-743b1e7eef47	cefc4b5a-ddda-41d5-8fa2-a1241aeec1f8	637b89e9-363f-48a7-aeb1-b02c61400612	d9f08263-1a26-4cd1-ac77-0a99d96abda5	e367120c-52a5-4f24-949a-e0e07c5f7810	v0.1	ce-v0.1	ae-v0.1	done	100	finished	manual	\N	\N	\N	2026-04-26 18:15:23.781921+09	2026-04-26 18:15:23.781921+09	2026-04-26 18:15:23.791336+09
b2bdf527-51e5-431f-8f35-cff4ede265d1	cefc4b5a-ddda-41d5-8fa2-a1241aeec1f8	637b89e9-363f-48a7-aeb1-b02c61400612	806326f8-3047-4934-89c4-097965351ec0	a2eb4ea4-fa25-4228-aaf9-f6624a1298ee	v0.1	ce-v0.1	ae-v0.1	done	100	finished	manual	\N	\N	\N	2026-04-26 19:30:41.654394+09	2026-04-26 19:30:41.654394+09	2026-04-26 19:30:41.663408+09
ef4f32c8-47bb-4711-a176-dd144f24d549	c4473457-9033-41ca-963c-69327eddad05	637b89e9-363f-48a7-aeb1-b02c61400612	2f18325e-61f3-4178-876d-cc4620d33187	68f7c38f-d69e-4fb6-80ef-58678f8e48d4	v0.1	ce-v0.1	ae-v0.1	done	100	finished	manual	\N	\N	\N	2026-05-03 19:36:56.640827+09	2026-05-03 19:36:56.640827+09	2026-05-03 19:36:56.662371+09
\.


--
-- Data for Name: notes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notes (note_id, user_id, title, description, created_at, updated_at) FROM stdin;
ab9dccb5-d7bb-443b-8be2-be4134867511	11111111-1111-1111-1111-111111111111	업로드 테스트 노트	파일 업로드 연결 테스트	2026-03-14 19:51:32.138403+09	\N
f1428c4a-f827-42bd-8a75-a878dfebcf48	11111111-1111-1111-1111-111111111111	test	분석 test	2026-04-07 16:21:22.102524+09	\N
db79ee91-4116-4309-8267-b53ee3066151	11111111-1111-1111-1111-111111111111	ㅇㅇㅇ	ㅇㅇㅇ	2026-04-07 18:15:39.967027+09	\N
cefc4b5a-ddda-41d5-8fa2-a1241aeec1f8	637b89e9-363f-48a7-aeb1-b02c61400612	테스트	없어용 아직	2026-04-26 18:10:28.493919+09	\N
c4473457-9033-41ca-963c-69327eddad05	637b89e9-363f-48a7-aeb1-b02c61400612	새로운 노트	아직 없음	2026-04-28 18:15:24.851468+09	\N
\.


--
-- Data for Name: uploads; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.uploads (upload_id, user_id, note_id, kind, storage, bucket, object_key, original_filename, url, content_type, size_bytes, checksum, status, created_at) FROM stdin;
666daa2d-41a6-4024-89a5-3472783f50ad	11111111-1111-1111-1111-111111111111	ab9dccb5-d7bb-443b-8be2-be4134867511	audio	s3	speechpt-dev	notes/ab9dccb5-d7bb-443b-8be2-be4134867511/uploads/666daa2d-41a6-4024-89a5-3472783f50ad/sample.wav	sample.wav	\N	audio/wav	123456	\N	pending	2026-03-14 19:53:28.882533+09
fabafc73-5d4d-4fc9-99bc-8c966d6f09b4	11111111-1111-1111-1111-111111111111	ab9dccb5-d7bb-443b-8be2-be4134867511	doucument	s3	speechpt-dev	notes/ab9dccb5-d7bb-443b-8be2-be4134867511/uploads/fabafc73-5d4d-4fc9-99bc-8c966d6f09b4/slides.pdf	slides.pdf	\N	application/pdf	456789	dummy-checksum	uploaded	2026-03-14 19:54:45.425975+09
22634a05-7014-4b51-a981-98754c20cce1	11111111-1111-1111-1111-111111111111	ab9dccb5-d7bb-443b-8be2-be4134867511	audio	s3	speechpt-dev	notes/ab9dccb5-d7bb-443b-8be2-be4134867511/uploads/22634a05-7014-4b51-a981-98754c20cce1/sample.wav	sample.wav	\N	audio/wav	123456	dummy-checksum	uploaded	2026-03-14 19:53:52.688358+09
c4dad3f6-29ce-4fb9-abcf-b6752873fc07	11111111-1111-1111-1111-111111111111	f1428c4a-f827-42bd-8a75-a878dfebcf48	document	s3	speechpt-dev	notes/f1428c4a-f827-42bd-8a75-a878dfebcf48/uploads/c4dad3f6-29ce-4fb9-abcf-b6752873fc07/test	test	\N	string	0	string	uploaded	2026-04-07 16:22:47.223388+09
c96633c3-e9b4-4e77-bea6-7bbdcd868fd1	11111111-1111-1111-1111-111111111111	f1428c4a-f827-42bd-8a75-a878dfebcf48	audio	s3	speechpt-dev	notes/f1428c4a-f827-42bd-8a75-a878dfebcf48/uploads/c96633c3-e9b4-4e77-bea6-7bbdcd868fd1/test1	test1	\N	string	0	string	uploaded	2026-04-07 16:24:44.866456+09
1216e6a4-e7e9-4bff-86c2-5c98eed49853	11111111-1111-1111-1111-111111111111	f1428c4a-f827-42bd-8a75-a878dfebcf48	document	s3	speechpt-dev	notes/f1428c4a-f827-42bd-8a75-a878dfebcf48/uploads/1216e6a4-e7e9-4bff-86c2-5c98eed49853/SpeechPT_김동균_3,4주차.pdf	SpeechPT_김동균_3,4주차.pdf	\N	application/pdf	2745269	\N	uploaded	2026-04-07 22:35:42.613076+09
554682d7-5d00-4a48-97a0-b42487c79579	11111111-1111-1111-1111-111111111111	f1428c4a-f827-42bd-8a75-a878dfebcf48	audio	s3	speechpt-dev	notes/f1428c4a-f827-42bd-8a75-a878dfebcf48/uploads/554682d7-5d00-4a48-97a0-b42487c79579/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-07 22:35:42.64481+09
c5770cba-f58e-4829-b6bb-c97cd839f768	11111111-1111-1111-1111-111111111111	db79ee91-4116-4309-8267-b53ee3066151	document	s3	speechpt-dev	notes/db79ee91-4116-4309-8267-b53ee3066151/uploads/c5770cba-f58e-4829-b6bb-c97cd839f768/SpeechPT_중간발표.pptx	SpeechPT_중간발표.pptx	\N	application/vnd.openxmlformats-officedocument.presentationml.presentation	167808	\N	uploaded	2026-04-07 22:36:01.401274+09
890cdb60-418f-43b6-a823-efa3a8167c9e	11111111-1111-1111-1111-111111111111	db79ee91-4116-4309-8267-b53ee3066151	audio	s3	speechpt-dev	notes/db79ee91-4116-4309-8267-b53ee3066151/uploads/890cdb60-418f-43b6-a823-efa3a8167c9e/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-07 22:36:01.430391+09
b7145eab-541a-4687-a237-ab571e903df3	11111111-1111-1111-1111-111111111111	ab9dccb5-d7bb-443b-8be2-be4134867511	document	s3	speechpt-dev	notes/ab9dccb5-d7bb-443b-8be2-be4134867511/uploads/b7145eab-541a-4687-a237-ab571e903df3/SpeechPT_김동균_3,4주차.pdf	SpeechPT_김동균_3,4주차.pdf	\N	application/pdf	2745269	\N	uploaded	2026-04-08 13:40:39.016543+09
7755bee0-1134-4125-a0e6-d27d8c2d2d86	11111111-1111-1111-1111-111111111111	ab9dccb5-d7bb-443b-8be2-be4134867511	audio	s3	speechpt-dev	notes/ab9dccb5-d7bb-443b-8be2-be4134867511/uploads/7755bee0-1134-4125-a0e6-d27d8c2d2d86/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-08 13:40:39.047472+09
f9f3cccb-97d5-4a63-a4fd-e8f60d9175e4	11111111-1111-1111-1111-111111111111	ab9dccb5-d7bb-443b-8be2-be4134867511	document	s3	speechpt-dev	notes/ab9dccb5-d7bb-443b-8be2-be4134867511/uploads/f9f3cccb-97d5-4a63-a4fd-e8f60d9175e4/SpeechPT_김동균_3,4주차.pdf	SpeechPT_김동균_3,4주차.pdf	\N	application/pdf	2745269	\N	uploaded	2026-04-08 13:42:11.716911+09
d92b7868-c3cb-41bc-9816-47da2900d0f6	11111111-1111-1111-1111-111111111111	ab9dccb5-d7bb-443b-8be2-be4134867511	audio	s3	speechpt-dev	notes/ab9dccb5-d7bb-443b-8be2-be4134867511/uploads/d92b7868-c3cb-41bc-9816-47da2900d0f6/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-08 13:42:11.743602+09
3ace8511-6ff1-469d-87e6-5ea75c68416c	11111111-1111-1111-1111-111111111111	ab9dccb5-d7bb-443b-8be2-be4134867511	document	s3	speechpt-dev	notes/ab9dccb5-d7bb-443b-8be2-be4134867511/uploads/3ace8511-6ff1-469d-87e6-5ea75c68416c/SpeechPT_김동균_3,4주차.pdf	SpeechPT_김동균_3,4주차.pdf	\N	application/pdf	2745269	\N	uploaded	2026-04-08 13:50:00.02872+09
f0c86e61-4300-4af0-8c85-15c64a2bfa93	11111111-1111-1111-1111-111111111111	ab9dccb5-d7bb-443b-8be2-be4134867511	audio	s3	speechpt-dev	notes/ab9dccb5-d7bb-443b-8be2-be4134867511/uploads/f0c86e61-4300-4af0-8c85-15c64a2bfa93/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-08 13:50:00.056494+09
407cec62-32a4-4ce1-a166-f38b9c870c16	11111111-1111-1111-1111-111111111111	ab9dccb5-d7bb-443b-8be2-be4134867511	document	s3	speechpt-dev	notes/ab9dccb5-d7bb-443b-8be2-be4134867511/uploads/407cec62-32a4-4ce1-a166-f38b9c870c16/SpeechPT_김동균_3,4주차.pdf	SpeechPT_김동균_3,4주차.pdf	\N	application/pdf	2745269	\N	uploaded	2026-04-08 13:53:15.243309+09
ec2d94a0-0a64-4867-a46d-c342c0cdc833	11111111-1111-1111-1111-111111111111	ab9dccb5-d7bb-443b-8be2-be4134867511	audio	s3	speechpt-dev	notes/ab9dccb5-d7bb-443b-8be2-be4134867511/uploads/ec2d94a0-0a64-4867-a46d-c342c0cdc833/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-08 13:53:15.254749+09
e0ed265d-70dd-4d74-aef4-332be89cf600	11111111-1111-1111-1111-111111111111	ab9dccb5-d7bb-443b-8be2-be4134867511	document	s3	speechpt-dev	notes/ab9dccb5-d7bb-443b-8be2-be4134867511/uploads/e0ed265d-70dd-4d74-aef4-332be89cf600/SpeechPT_김동균_3,4주차.pdf	SpeechPT_김동균_3,4주차.pdf	\N	application/pdf	2745269	\N	uploaded	2026-04-08 13:55:44.611371+09
f57f99b7-ba5a-49c2-bbf6-e29d9a27a9a9	11111111-1111-1111-1111-111111111111	ab9dccb5-d7bb-443b-8be2-be4134867511	audio	s3	speechpt-dev	notes/ab9dccb5-d7bb-443b-8be2-be4134867511/uploads/f57f99b7-ba5a-49c2-bbf6-e29d9a27a9a9/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-08 13:55:44.632961+09
d9834239-e834-473d-9ff9-922286d3acd7	11111111-1111-1111-1111-111111111111	ab9dccb5-d7bb-443b-8be2-be4134867511	document	s3	speechpt-dev	notes/ab9dccb5-d7bb-443b-8be2-be4134867511/uploads/d9834239-e834-473d-9ff9-922286d3acd7/SpeechPT_김동균_3,4주차.pdf	SpeechPT_김동균_3,4주차.pdf	\N	application/pdf	2745269	\N	uploaded	2026-04-08 14:02:54.096212+09
b247bb1a-ea0b-4e4f-b000-46688487eabd	11111111-1111-1111-1111-111111111111	ab9dccb5-d7bb-443b-8be2-be4134867511	audio	s3	speechpt-dev	notes/ab9dccb5-d7bb-443b-8be2-be4134867511/uploads/b247bb1a-ea0b-4e4f-b000-46688487eabd/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-08 14:02:54.113748+09
9c4cccc7-3b22-4daf-b88d-b42a7d625183	11111111-1111-1111-1111-111111111111	f1428c4a-f827-42bd-8a75-a878dfebcf48	document	s3	speechpt-dev	notes/f1428c4a-f827-42bd-8a75-a878dfebcf48/uploads/9c4cccc7-3b22-4daf-b88d-b42a7d625183/Week02_Simplified Instructional Computer.pdf	Week02_Simplified Instructional Computer.pdf	\N	application/pdf	3474677	\N	uploaded	2026-04-08 14:18:42.918296+09
25ac509b-2b20-48bc-8207-1cde8b54bd9e	11111111-1111-1111-1111-111111111111	f1428c4a-f827-42bd-8a75-a878dfebcf48	audio	s3	speechpt-dev	notes/f1428c4a-f827-42bd-8a75-a878dfebcf48/uploads/25ac509b-2b20-48bc-8207-1cde8b54bd9e/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-08 14:18:42.945001+09
b46edb72-4be5-4f57-98f8-98d3b1bd2a9c	11111111-1111-1111-1111-111111111111	f1428c4a-f827-42bd-8a75-a878dfebcf48	document	s3	speechpt-dev	notes/f1428c4a-f827-42bd-8a75-a878dfebcf48/uploads/b46edb72-4be5-4f57-98f8-98d3b1bd2a9c/SpeechPT_김동균_3,4주차.pdf	SpeechPT_김동균_3,4주차.pdf	\N	application/pdf	2745269	\N	uploaded	2026-04-08 14:22:33.410526+09
9a6f3d2c-be38-412e-a193-d3b2daaa8a32	11111111-1111-1111-1111-111111111111	f1428c4a-f827-42bd-8a75-a878dfebcf48	audio	s3	speechpt-dev	notes/f1428c4a-f827-42bd-8a75-a878dfebcf48/uploads/9a6f3d2c-be38-412e-a193-d3b2daaa8a32/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-08 14:22:33.418429+09
ec436027-9a6a-440d-ba85-83be2185df88	11111111-1111-1111-1111-111111111111	f1428c4a-f827-42bd-8a75-a878dfebcf48	document	s3	speechpt-dev	notes/f1428c4a-f827-42bd-8a75-a878dfebcf48/uploads/ec436027-9a6a-440d-ba85-83be2185df88/SpeechPT_김동균_3,4주차.pdf	SpeechPT_김동균_3,4주차.pdf	\N	application/pdf	2745269	\N	uploaded	2026-04-08 14:26:49.130031+09
5c0bf709-b46c-4be0-a8f6-9b46032437f0	11111111-1111-1111-1111-111111111111	f1428c4a-f827-42bd-8a75-a878dfebcf48	audio	s3	speechpt-dev	notes/f1428c4a-f827-42bd-8a75-a878dfebcf48/uploads/5c0bf709-b46c-4be0-a8f6-9b46032437f0/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-08 14:26:49.141549+09
23f8b098-248e-4e31-92fc-6d3cb6400427	11111111-1111-1111-1111-111111111111	db79ee91-4116-4309-8267-b53ee3066151	document	s3	speechpt-dev	notes/db79ee91-4116-4309-8267-b53ee3066151/uploads/23f8b098-248e-4e31-92fc-6d3cb6400427/SpeechPT_주민규_3,4주차.pdf	SpeechPT_주민규_3,4주차.pdf	\N	application/pdf	2762221	\N	uploaded	2026-04-08 18:42:30.328196+09
ceccd05d-a10c-4eb5-aa7e-e406c403ad93	11111111-1111-1111-1111-111111111111	db79ee91-4116-4309-8267-b53ee3066151	audio	s3	speechpt-dev	notes/db79ee91-4116-4309-8267-b53ee3066151/uploads/ceccd05d-a10c-4eb5-aa7e-e406c403ad93/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-08 18:42:30.363796+09
f898cdbb-b384-42af-badc-3c19fffbc261	11111111-1111-1111-1111-111111111111	db79ee91-4116-4309-8267-b53ee3066151	document	s3	speechpt-dev	notes/db79ee91-4116-4309-8267-b53ee3066151/uploads/f898cdbb-b384-42af-badc-3c19fffbc261/SpeechPT_중간발표.pptx	SpeechPT_중간발표.pptx	\N	application/vnd.openxmlformats-officedocument.presentationml.presentation	167808	\N	uploaded	2026-04-09 22:05:20.98457+09
38e01823-0f92-41a8-88df-cb4f2f19a15e	11111111-1111-1111-1111-111111111111	db79ee91-4116-4309-8267-b53ee3066151	audio	s3	speechpt-dev	notes/db79ee91-4116-4309-8267-b53ee3066151/uploads/38e01823-0f92-41a8-88df-cb4f2f19a15e/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-09 22:05:21.031113+09
8fe2338b-7f84-4204-b730-ffc303d2e2ea	11111111-1111-1111-1111-111111111111	db79ee91-4116-4309-8267-b53ee3066151	document	s3	speechpt-dev	notes/db79ee91-4116-4309-8267-b53ee3066151/uploads/8fe2338b-7f84-4204-b730-ffc303d2e2ea/SpeechPT_주민규_3,4주차.pdf	SpeechPT_주민규_3,4주차.pdf	\N	application/pdf	2762221	\N	uploaded	2026-04-09 22:13:14.36509+09
9d9a27be-2091-4a65-afeb-1f41a3ef3cfd	11111111-1111-1111-1111-111111111111	db79ee91-4116-4309-8267-b53ee3066151	audio	s3	speechpt-dev	notes/db79ee91-4116-4309-8267-b53ee3066151/uploads/9d9a27be-2091-4a65-afeb-1f41a3ef3cfd/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-09 22:13:14.394721+09
c374b878-00e1-41b1-8e1e-a7e942d21660	11111111-1111-1111-1111-111111111111	db79ee91-4116-4309-8267-b53ee3066151	document	s3	speechpt-dev	notes/db79ee91-4116-4309-8267-b53ee3066151/uploads/c374b878-00e1-41b1-8e1e-a7e942d21660/대학생진로준비도검사결과_주민규.pdf	대학생진로준비도검사결과_주민규.pdf	\N	application/pdf	87478	\N	uploaded	2026-04-09 23:00:22.216655+09
7ddee677-4d68-4ccb-bf03-c3d8cf562661	11111111-1111-1111-1111-111111111111	db79ee91-4116-4309-8267-b53ee3066151	audio	s3	speechpt-dev	notes/db79ee91-4116-4309-8267-b53ee3066151/uploads/7ddee677-4d68-4ccb-bf03-c3d8cf562661/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-09 23:00:22.243229+09
d9f08263-1a26-4cd1-ac77-0a99d96abda5	637b89e9-363f-48a7-aeb1-b02c61400612	cefc4b5a-ddda-41d5-8fa2-a1241aeec1f8	document	s3	speechpt-dev	notes/cefc4b5a-ddda-41d5-8fa2-a1241aeec1f8/uploads/d9f08263-1a26-4cd1-ac77-0a99d96abda5/시프 1주차.pdf	시프 1주차.pdf	\N	application/pdf	1556760	\N	uploaded	2026-04-26 18:15:23.714012+09
e367120c-52a5-4f24-949a-e0e07c5f7810	637b89e9-363f-48a7-aeb1-b02c61400612	cefc4b5a-ddda-41d5-8fa2-a1241aeec1f8	audio	s3	speechpt-dev	notes/cefc4b5a-ddda-41d5-8fa2-a1241aeec1f8/uploads/e367120c-52a5-4f24-949a-e0e07c5f7810/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-26 18:15:23.766343+09
806326f8-3047-4934-89c4-097965351ec0	637b89e9-363f-48a7-aeb1-b02c61400612	cefc4b5a-ddda-41d5-8fa2-a1241aeec1f8	document	s3	speechpt-dev	notes/cefc4b5a-ddda-41d5-8fa2-a1241aeec1f8/uploads/806326f8-3047-4934-89c4-097965351ec0/[SpeechPT] 파란학기 신청서 및 계획서.pdf	[SpeechPT] 파란학기 신청서 및 계획서.pdf	\N	application/pdf	1865907	\N	uploaded	2026-04-26 19:30:41.555781+09
a2eb4ea4-fa25-4228-aaf9-f6624a1298ee	637b89e9-363f-48a7-aeb1-b02c61400612	cefc4b5a-ddda-41d5-8fa2-a1241aeec1f8	audio	s3	speechpt-dev	notes/cefc4b5a-ddda-41d5-8fa2-a1241aeec1f8/uploads/a2eb4ea4-fa25-4228-aaf9-f6624a1298ee/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-04-26 19:30:41.640583+09
1de11144-4e56-40c3-b00a-ec64ec6c2251	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	document	s3	speechpt-dev	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/1de11144-4e56-40c3-b00a-ec64ec6c2251/주민규 롤링페이퍼.pdf	주민규 롤링페이퍼.pdf	\N	application/pdf	6249	\N	pending	2026-05-03 18:03:00.303007+09
60817dc8-c5a1-492f-af3e-74673cd8c01d	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	audio	s3	speechpt-dev	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/60817dc8-c5a1-492f-af3e-74673cd8c01d/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	pending	2026-05-03 18:03:01.982954+09
ca47ac60-55f1-49c2-bef7-c47a6b926fdf	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	document	s3	speechpt-dev	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/ca47ac60-55f1-49c2-bef7-c47a6b926fdf/엑스 배너 현금연수증.pdf	엑스 배너 현금연수증.pdf	\N	application/pdf	57740	\N	pending	2026-05-03 18:03:15.322519+09
d301bac7-c5b0-4554-ae5b-35c81232c135	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	audio	s3	speechpt-dev	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/d301bac7-c5b0-4554-ae5b-35c81232c135/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	pending	2026-05-03 18:03:16.842382+09
947841e2-30db-4940-bd1c-ad4e597fedcc	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	document	s3	speechpt-dev	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/947841e2-30db-4940-bd1c-ad4e597fedcc/[SpeechPT] 파란학기 신청서 및 계획서.pdf	[SpeechPT] 파란학기 신청서 및 계획서.pdf	\N	application/pdf	1865907	\N	pending	2026-05-03 18:42:55.495315+09
c9098cbe-7481-469a-8950-d58d062e0eba	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	audio	s3	speechpt-dev	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/c9098cbe-7481-469a-8950-d58d062e0eba/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	pending	2026-05-03 18:45:21.935277+09
00bd4fbc-e9c5-431c-860f-fab11bd4781b	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	document	s3	speechpt-dev	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/00bd4fbc-e9c5-431c-860f-fab11bd4781b/과제 2 모범 답안.pdf	과제 2 모범 답안.pdf	\N	application/pdf	93467	\N	pending	2026-05-03 18:50:18.18129+09
8db100ad-8543-4ef2-936a-8799e4ec4a1a	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	audio	s3	speechpt-dev	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/8db100ad-8543-4ef2-936a-8799e4ec4a1a/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	pending	2026-05-03 18:42:57.190877+09
056997f6-ab7b-41ed-9734-56bd413c323d	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	document	s3	speechpt-dev	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/056997f6-ab7b-41ed-9734-56bd413c323d/[SpeechPT] 파란학기 신청서 및 계획서.pdf	[SpeechPT] 파란학기 신청서 및 계획서.pdf	\N	application/pdf	1865907	\N	pending	2026-05-03 18:45:20.321124+09
925acc16-0d70-425c-827a-07654fcbda4a	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	audio	s3	speechpt-dev	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/925acc16-0d70-425c-827a-07654fcbda4a/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	pending	2026-05-03 18:50:19.447412+09
fc2e4ce0-d557-4084-ad27-4a837fede46a	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	document	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/fc2e4ce0-d557-4084-ad27-4a837fede46a/과제 2 모범 답안.pdf	과제 2 모범 답안.pdf	\N	application/pdf	93467	\N	pending	2026-05-03 18:55:06.562692+09
34509944-d7ea-4780-abce-9eb75bd2727b	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	audio	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/34509944-d7ea-4780-abce-9eb75bd2727b/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	pending	2026-05-03 18:55:08.24181+09
9cdd62f4-f31e-456a-bd55-d1749ae869bf	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	document	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/9cdd62f4-f31e-456a-bd55-d1749ae869bf/과제 2 모범 답안.pdf	과제 2 모범 답안.pdf	\N	application/pdf	93467	\N	pending	2026-05-03 18:58:09.050713+09
1d4fd56c-fa8d-4608-9069-0a369b698799	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	audio	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/1d4fd56c-fa8d-4608-9069-0a369b698799/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	pending	2026-05-03 18:58:10.185557+09
533b3476-0cd6-427b-86d4-1a6b25e12167	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	document	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/533b3476-0cd6-427b-86d4-1a6b25e12167/과제 2 모범 답안.pdf	과제 2 모범 답안.pdf	\N	application/pdf	93467	\N	pending	2026-05-03 19:05:55.49541+09
7f90ebc1-f266-4c00-a186-fbaf1728228e	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	audio	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/7f90ebc1-f266-4c00-a186-fbaf1728228e/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	pending	2026-05-03 19:05:57.986317+09
53a593d4-035e-485c-a083-a6b2a2828930	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	document	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/53a593d4-035e-485c-a083-a6b2a2828930/과제 2 모범 답안.pdf	과제 2 모범 답안.pdf	\N	application/pdf	93467	\N	pending	2026-05-03 19:10:58.585944+09
9ba6438a-df60-4545-93ea-4db3d83f3ea4	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	audio	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/9ba6438a-df60-4545-93ea-4db3d83f3ea4/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	pending	2026-05-03 19:11:00.702812+09
ac0b3b5a-e8ab-4905-8475-24a2b4762dc9	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	document	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/ac0b3b5a-e8ab-4905-8475-24a2b4762dc9/과제 2 모범 답안.pdf	과제 2 모범 답안.pdf	\N	application/pdf	93467	\N	pending	2026-05-03 19:14:39.336898+09
12e2376e-f9dd-4244-900a-eb7799cbfeff	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	audio	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/12e2376e-f9dd-4244-900a-eb7799cbfeff/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	pending	2026-05-03 19:14:41.561745+09
cee47ce7-39cf-4010-aecd-6d50743d8f1a	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	document	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/cee47ce7-39cf-4010-aecd-6d50743d8f1a/과제 2 모범 답안.pdf	과제 2 모범 답안.pdf	\N	application/pdf	93467	\N	pending	2026-05-03 19:22:10.43624+09
15a6e3b9-7cdf-42fe-8796-94707126e1e7	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	audio	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/15a6e3b9-7cdf-42fe-8796-94707126e1e7/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	pending	2026-05-03 19:22:11.723325+09
c18b1ca9-e569-4fe8-9cf9-2dafd8011941	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	document	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/c18b1ca9-e569-4fe8-9cf9-2dafd8011941/과제 2 모범 답안.pdf	과제 2 모범 답안.pdf	\N	application/pdf	93467	\N	pending	2026-05-03 19:31:49.101191+09
586ae715-0961-4836-954e-2cc9d5431748	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	audio	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/586ae715-0961-4836-954e-2cc9d5431748/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	pending	2026-05-03 19:31:52.093843+09
2f18325e-61f3-4178-876d-cc4620d33187	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	document	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/2f18325e-61f3-4178-876d-cc4620d33187/과제 2 모범 답안.pdf	과제 2 모범 답안.pdf	\N	application/pdf	93467	\N	uploaded	2026-05-03 19:36:55.869187+09
68f7c38f-d69e-4fb6-80ef-58678f8e48d4	637b89e9-363f-48a7-aeb1-b02c61400612	c4473457-9033-41ca-963c-69327eddad05	audio	s3	speechpt-upload	notes/c4473457-9033-41ca-963c-69327eddad05/uploads/68f7c38f-d69e-4fb6-80ef-58678f8e48d4/viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	viralaudio-descent-whoosh-long-cinematic-sound-effect-405921.wav	\N	audio/wav	1064526	\N	uploaded	2026-05-03 19:36:56.349561+09
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (user_id, email, password_hash, name, provider, provider_id, created_at) FROM stdin;
11111111-1111-1111-1111-111111111111	dummy@speechpt.com	dummy_hash	Dummy User	local	\N	2026-03-12 15:30:22.425637+09
1ea6f942-7f94-461f-b794-f9d64b053b33	test@example.com	ztDIE6TSFxjLnBMz7wPHTDtBL38qJ-8iBrLBLZw6eNm4ZaTxjrl58Sat1BRLeEGw	test	local	\N	2026-04-26 18:09:39.08248+09
637b89e9-363f-48a7-aeb1-b02c61400612	zzmg11251125@gmail.com	Kk3pr1zDAuyNPT-5em7NuRn9OhQiTjPtDy_fvdhF4EQ-W5aBajASznbhB9BcPnkA	zzmg11251125	local	\N	2026-04-26 18:10:14.738494+09
3e2c0f76-140f-4d01-8cee-6cb310542f4e	alsrb1125@ajou.ac.kr	v1EWCxUGco1t-_k7iamLsHWU4oSiiCVNMIEEuKMCcM_RxHInB6Lm9BdPqO358vWg	alsrb1125	local	\N	2026-04-26 18:18:51.608413+09
\.


--
-- Name: analyses analyses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analyses
    ADD CONSTRAINT analyses_pkey PRIMARY KEY (analysis_id);


--
-- Name: notes notes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notes
    ADD CONSTRAINT notes_pkey PRIMARY KEY (note_id);


--
-- Name: uploads uploads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uploads
    ADD CONSTRAINT uploads_pkey PRIMARY KEY (upload_id);


--
-- Name: uploads uq_upload_bucket_object_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uploads
    ADD CONSTRAINT uq_upload_bucket_object_key UNIQUE (bucket, object_key);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: ix_analysis_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_analysis_created_at ON public.analyses USING btree (created_at);


--
-- Name: ix_analysis_note_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_analysis_note_id ON public.analyses USING btree (note_id);


--
-- Name: ix_analysis_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_analysis_status ON public.analyses USING btree (status);


--
-- Name: ix_upload_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_upload_created_at ON public.uploads USING btree (created_at);


--
-- Name: ix_upload_note_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_upload_note_id ON public.uploads USING btree (note_id);


--
-- Name: ix_upload_note_kind; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_upload_note_kind ON public.uploads USING btree (note_id, kind);


--
-- Name: analyses analyses_audio_upload_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analyses
    ADD CONSTRAINT analyses_audio_upload_id_fkey FOREIGN KEY (audio_upload_id) REFERENCES public.uploads(upload_id) ON DELETE RESTRICT;


--
-- Name: analyses analyses_document_upload_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analyses
    ADD CONSTRAINT analyses_document_upload_id_fkey FOREIGN KEY (document_upload_id) REFERENCES public.uploads(upload_id) ON DELETE RESTRICT;


--
-- Name: analyses analyses_note_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analyses
    ADD CONSTRAINT analyses_note_id_fkey FOREIGN KEY (note_id) REFERENCES public.notes(note_id) ON DELETE CASCADE;


--
-- Name: analyses analyses_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analyses
    ADD CONSTRAINT analyses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: notes notes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notes
    ADD CONSTRAINT notes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: uploads uploads_note_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uploads
    ADD CONSTRAINT uploads_note_id_fkey FOREIGN KEY (note_id) REFERENCES public.notes(note_id) ON DELETE SET NULL;


--
-- Name: uploads uploads_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uploads
    ADD CONSTRAINT uploads_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict bgOJgfYruMqxmDy25jbdHDZchgZiWW46I5rBgvuKjzgzIOG2hbRJPBwZmAZ4tlH

