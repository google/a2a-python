# Changelog

## [0.2.10](https://github.com/a2aproject/a2a-python/compare/v0.2.9...v0.2.10) (2025-06-30)


### ⚠ BREAKING CHANGES

* Update to A2A Spec Version [0.2.5](https://github.com/a2aproject/A2A/releases/tag/v0.2.5) ([#197](https://github.com/a2aproject/a2a-python/issues/197))

### Features

* Add `append` and `last_chunk` to `add_artifact` method on `TaskUpdater` ([#186](https://github.com/a2aproject/a2a-python/issues/186)) ([8c6560f](https://github.com/a2aproject/a2a-python/commit/8c6560fd403887fab9d774bfcc923a5f6f459364))
* add a2a routes to existing app ([#188](https://github.com/a2aproject/a2a-python/issues/188)) ([32fecc7](https://github.com/a2aproject/a2a-python/commit/32fecc7194a61c2f5be0b8795d5dc17cdbab9040))
* Add middleware to the client SDK ([#171](https://github.com/a2aproject/a2a-python/issues/171)) ([efaabd3](https://github.com/a2aproject/a2a-python/commit/efaabd3b71054142109b553c984da1d6e171db24))
* Add more task state management methods to TaskUpdater ([#208](https://github.com/a2aproject/a2a-python/issues/208)) ([2b3bf6d](https://github.com/a2aproject/a2a-python/commit/2b3bf6d53ac37ed93fc1b1c012d59c19060be000))
* raise error for tasks in terminal states ([#215](https://github.com/a2aproject/a2a-python/issues/215)) ([a0bf13b](https://github.com/a2aproject/a2a-python/commit/a0bf13b208c90b439b4be1952c685e702c4917a0))

### Bug Fixes

* `consume_all` doesn't catch `asyncio.TimeoutError` in python 3.10 ([#216](https://github.com/a2aproject/a2a-python/issues/216)) ([39307f1](https://github.com/a2aproject/a2a-python/commit/39307f15a1bb70eb77aee2211da038f403571242))
* Append metadata and context id when processing TaskStatusUpdateE… ([#238](https://github.com/a2aproject/a2a-python/issues/238)) ([e106020](https://github.com/a2aproject/a2a-python/commit/e10602033fdd4f4e6b61af717ffc242d772545b3))
* Fix reference to `grpc.aio.ServicerContext` ([#237](https://github.com/a2aproject/a2a-python/issues/237)) ([0c1987b](https://github.com/a2aproject/a2a-python/commit/0c1987bb85f3e21089789ee260a0c62ac98b66a5))
* Fixes Short Circuit clause for context ID ([#236](https://github.com/a2aproject/a2a-python/issues/236)) ([a5509e6](https://github.com/a2aproject/a2a-python/commit/a5509e6b37701dfb5c729ccc12531e644a12f8ae))
* Resolve `APIKeySecurityScheme` parsing failed ([#226](https://github.com/a2aproject/a2a-python/issues/226)) ([aa63b98](https://github.com/a2aproject/a2a-python/commit/aa63b982edc2a07fd0df0b01fb9ad18d30b35a79))
* send notifications on message not streaming ([#219](https://github.com/a2aproject/a2a-python/issues/219)) ([91539d6](https://github.com/a2aproject/a2a-python/commit/91539d69e5c757712c73a41ab95f1ec6656ef5cd)), closes [#218](https://github.com/a2aproject/a2a-python/issues/218)

## [0.2.9](https://github.com/a2aproject/a2a-python/compare/v0.2.8...v0.2.9) (2025-06-24)

### Bug Fixes

* Set `protobuf==5.29.5` and `fastapi>=0.115.2` to prevent version conflicts ([#224](https://github.com/a2aproject/a2a-python/issues/224)) ([1412a85](https://github.com/a2aproject/a2a-python/commit/1412a855b4980d8373ed1cea38c326be74069633))

## [0.2.8](https://github.com/a2aproject/a2a-python/compare/v0.2.7...v0.2.8) (2025-06-12)


### Features

* Add HTTP Headers to ServerCallContext for Improved Handler Access ([#182](https://github.com/a2aproject/a2a-python/issues/182)) ([d5e5f5f](https://github.com/a2aproject/a2a-python/commit/d5e5f5f7e7a3cab7de13cff545a874fc58d85e46))
* Update A2A types from specification 🤖 ([#191](https://github.com/a2aproject/a2a-python/issues/191)) ([174230b](https://github.com/a2aproject/a2a-python/commit/174230bf6dfb6bf287d233a101b98cc4c79cad19))


### Bug Fixes

* Add `protobuf==6.31.1` to dependencies ([#189](https://github.com/a2aproject/a2a-python/issues/189)) ([ae1c31c](https://github.com/a2aproject/a2a-python/commit/ae1c31c1da47f6965c02e0564dc7d3791dd03e2c)), closes [#185](https://github.com/a2aproject/a2a-python/issues/185)

## [0.2.7](https://github.com/a2aproject/a2a-python/compare/v0.2.6...v0.2.7) (2025-06-11)


### Features

* Update A2A types from specification 🤖 ([#179](https://github.com/a2aproject/a2a-python/issues/179)) ([3ef4240](https://github.com/a2aproject/a2a-python/commit/3ef42405f6096281fe90b1df399731bd009bde12))

## [0.2.6](https://github.com/a2aproject/a2a-python/compare/v0.2.5...v0.2.6) (2025-06-09)


### ⚠ BREAKING CHANGES

* Add FastAPI JSONRPC Application ([#104](https://github.com/a2aproject/a2a-python/issues/104))

### Features

* Add FastAPI JSONRPC Application ([#104](https://github.com/a2aproject/a2a-python/issues/104)) ([0e66e1f](https://github.com/a2aproject/a2a-python/commit/0e66e1f81f98d7e2cf50b1c100e35d13ad7149dc))
* Add gRPC server and client support ([#162](https://github.com/a2aproject/a2a-python/issues/162)) ([a981605](https://github.com/a2aproject/a2a-python/commit/a981605dbb32e87bd241b64bf2e9bb52831514d1))
* add reject method to task_updater ([#147](https://github.com/a2aproject/a2a-python/issues/147)) ([2a6ef10](https://github.com/a2aproject/a2a-python/commit/2a6ef109f8b743f8eb53d29090cdec7df143b0b4))
* Add timestamp to `TaskStatus` updates on `TaskUpdater` ([#140](https://github.com/a2aproject/a2a-python/issues/140)) ([0c9df12](https://github.com/a2aproject/a2a-python/commit/0c9df125b740b947b0e4001421256491b5f87920))
* **spec:** Add an optional iconUrl field to the AgentCard 🤖 ([a1025f4](https://github.com/a2aproject/a2a-python/commit/a1025f406acd88e7485a5c0f4dd8a42488c41fa2))


### Bug Fixes

* Correctly adapt starlette BaseUser to A2A User ([#133](https://github.com/a2aproject/a2a-python/issues/133)) ([88d45eb](https://github.com/a2aproject/a2a-python/commit/88d45ebd935724e6c3ad614bf503defae4de5d85))
* Event consumer should stop on input_required ([#167](https://github.com/a2aproject/a2a-python/issues/167)) ([51c2d8a](https://github.com/a2aproject/a2a-python/commit/51c2d8addf9e89a86a6834e16deb9f4ac0e05cc3))
* Fix Release Version ([#161](https://github.com/a2aproject/a2a-python/issues/161)) ([011d632](https://github.com/a2aproject/a2a-python/commit/011d632b27b201193813ce24cf25e28d1335d18e))
* generate StrEnum types for enums ([#134](https://github.com/a2aproject/a2a-python/issues/134)) ([0c49dab](https://github.com/a2aproject/a2a-python/commit/0c49dabcdb9d62de49fda53d7ce5c691b8c1591c))
* library should released as 0.2.6 ([d8187e8](https://github.com/a2aproject/a2a-python/commit/d8187e812d6ac01caedf61d4edaca522e583d7da))
* remove error types from enqueable events ([#138](https://github.com/a2aproject/a2a-python/issues/138)) ([511992f](https://github.com/a2aproject/a2a-python/commit/511992fe585bd15e956921daeab4046dc4a50a0a))
* **stream:** don't block event loop in EventQueue ([#151](https://github.com/a2aproject/a2a-python/issues/151)) ([efd9080](https://github.com/a2aproject/a2a-python/commit/efd9080b917c51d6e945572fd123b07f20974a64))
* **task_updater:** fix potential duplicate artifact_id from default v… ([#156](https://github.com/a2aproject/a2a-python/issues/156)) ([1f0a769](https://github.com/a2aproject/a2a-python/commit/1f0a769c1027797b2f252e4c894352f9f78257ca))


### Documentation

* remove final and metadata fields from docstring ([#66](https://github.com/a2aproject/a2a-python/issues/66)) ([3c50ee1](https://github.com/a2aproject/a2a-python/commit/3c50ee1f64c103a543c8afb6d2ac3a11063b0f43))
* Update Links to Documentation Site ([5e7d418](https://github.com/a2aproject/a2a-python/commit/5e7d4180f7ae0ebeb76d976caa5ef68b4277ce54))

## [0.2.5](https://github.com/a2aproject/a2a-python/compare/v0.2.4...v0.2.5) (2025-05-27)


### Features

* Add a User representation to ServerCallContext ([#116](https://github.com/a2aproject/a2a-python/issues/116)) ([2cc2a0d](https://github.com/a2aproject/a2a-python/commit/2cc2a0de93631aa162823d43fe488173ed8754dc))
* Add functionality for extended agent card.  ([#31](https://github.com/a2aproject/a2a-python/issues/31)) ([20f0826](https://github.com/a2aproject/a2a-python/commit/20f0826a2cb9b77b89b85189fd91e7cd62318a30))
* Introduce a ServerCallContext ([#94](https://github.com/a2aproject/a2a-python/issues/94)) ([85b521d](https://github.com/a2aproject/a2a-python/commit/85b521d8a790dacb775ef764a66fbdd57b180da3))


### Bug Fixes

* fix hello world example for python 3.12 ([#98](https://github.com/a2aproject/a2a-python/issues/98)) ([536e4a1](https://github.com/a2aproject/a2a-python/commit/536e4a11f2f32332968a06e7d0bc4615e047a56c))
* Remove unused dependencies and update py version ([#119](https://github.com/a2aproject/a2a-python/issues/119)) ([9f8bc02](https://github.com/a2aproject/a2a-python/commit/9f8bc023b45544942583818968f3d320e5ff1c3b))
* Update hello world test client to match sdk behavior. Also down-level required python version ([#117](https://github.com/a2aproject/a2a-python/issues/117)) ([04c7c45](https://github.com/a2aproject/a2a-python/commit/04c7c452f5001d69524d94095d11971c1e857f75))
* Update the google adk demos to use ADK v1.0 ([#95](https://github.com/a2aproject/a2a-python/issues/95)) ([c351656](https://github.com/a2aproject/a2a-python/commit/c351656a91c37338668b0cd0c4db5fedd152d743))


### Documentation

* Update README for Python 3.10+ support ([#90](https://github.com/a2aproject/a2a-python/issues/90)) ([e0db20f](https://github.com/a2aproject/a2a-python/commit/e0db20ffc20aa09ee68304cc7e2a67c32ecdd6a8))

## [0.2.4](https://github.com/a2aproject/a2a-python/compare/v0.2.3...v0.2.4) (2025-05-22)

### Features

* Update to support python 3.10 ([#85](https://github.com/a2aproject/a2a-python/issues/85)) ([fd9c3b5](https://github.com/a2aproject/a2a-python/commit/fd9c3b5b0bbef509789a701171d95f690c84750b))


### Bug Fixes

* Throw exception for task_id mismatches ([#70](https://github.com/a2aproject/a2a-python/issues/70)) ([a9781b5](https://github.com/a2aproject/a2a-python/commit/a9781b589075280bfaaab5742d8b950916c9de74))

## [0.2.3](https://github.com/a2aproject/a2a-python/compare/v0.2.2...v0.2.3) (2025-05-20)


### Features

* Add request context builder with referenceTasks ([#56](https://github.com/a2aproject/a2a-python/issues/56)) ([f20bfe7](https://github.com/a2aproject/a2a-python/commit/f20bfe74b8cc854c9c29720b2ea3859aff8f509e))

## [0.2.2](https://github.com/a2aproject/a2a-python/compare/v0.2.1...v0.2.2) (2025-05-20)


### Documentation

* Write/Update Docstrings for Classes/Methods ([#59](https://github.com/a2aproject/a2a-python/issues/59)) ([9f773ef](https://github.com/a2aproject/a2a-python/commit/9f773eff4dddc4eec723d519d0050f21b9ccc042))
