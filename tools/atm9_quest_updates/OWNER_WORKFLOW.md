# Рабочий маршрут владельца Original / Modified

`tools/update_atm9_quests.py` — единая команда для подготовки review-результата перевода. Она не пишет в опубликованное дерево, не обновляет моды и не переключает активный профиль автоматически. Все выходные каталоги должны быть отдельными и пустыми; source snapshots/review recipes храните в `artifacts` или отдельном source-only `maintenance/quest-updates`, вне `tools`, `library` и runtime-каталогов. Это исключает самоссылку fingerprint на собственный recipe.

## Текущая опубликованная версия

Сначала выполните штатную подготовку и проверку исходной карточки. Для Original это `tools/prepare_pack.py` и `tools/verify_upstream.py`; для Modified — `tools/restore_modified.py` и `tools/verify_modified.py`. Обычная CI-сборка продолжает использовать закреплённые cache/profile/lock и не обращается за новым переводом.

```powershell
python tools/update_atm9_quests.py snapshot-published `
  --kind original --published <published-source> `
  --out <research>/published-inputs.json
```

Для Modified замените `--kind original` на `--kind modified`. Команда запускает **настоящий текущий verifier** этой сборки, затем фиксирует все runtime-файлы, авторские строки, support, дополнения, физические инструменты/метаданные и прежние localization pins. Количество support не зашито. Снимок нельзя получать из личной установленной игры: `saves`, `logs/latest.log`, неизвестный конфиг, JAR или source-tool отклоняются.

Повторная подготовка нуждается в чистом авторском входе. Его можно воспроизвести из точной опубликованной копии текущей версии:

```powershell
python tools/update_atm9_quests.py stage-author `
  --published <published-source> `
  --published-snapshot <research>/published-inputs.json `
  --out <research>/pristine-author
```

Команда сначала проверяет **весь** опубликованный снимок. Затем восстанавливает только точные авторские строки из закреплённого upstream lock; known display-spans обращаются в памяти до начала записи. Все остальные исходные JAR/файлы копируются с прежними hash. RU/notices/presets/дополнительные моды, отсутствующие в author lock, перечисляются в `tools/atm9-quest-author-stage.json` как **известные проверенные неавторские файлы**, а не silently discarded unknowns. Настоящий native RU включается только если он реально входит в author lock. Финальная проверка требует все исходные SHA/размеры и точный состав BASE JAR. Вход остаётся нетронутым.

`stage-author` воспроизводит авторский BASE **текущей закреплённой версии**. Он не выдаёт прежнюю версию за свежую загрузку следующего релиза.

## Явный импорт новой авторской версии

Владелец отдельно скачивает настоящий новый авторский релиз, сохраняет точный архив/происхождение, обновляет его upstream lock/платформу и подготавливает свежий author staging штатным importer. Это независимое обновление состава, не операция перевода. Новому релизу нельзя подставлять старый upstream lock или старый review-inputs recipe.

Получение нового Scriptora/community перевода — отдельное явное действие:

```powershell
python tools/update_atm9_quests.py refresh-provider `
  --fresh-author <new-pristine-author> `
  --upstream-lock <new-upstream-lock.json> `
  --previous-cache tools/atm9_ru_future/community-source.json `
  --out <research>/fresh-community.json `
  --report <research>/provider-refresh.json
```

Только `refresh-provider` обращается к внешнему провайдеру. При его недоступности прежний проверенный source-only cache сохраняется, старые EN-привязки не обновляются. `--require-fresh` включает явную ошибку этого шага по запросу владельца. Для нового/изменённого EN можно передать `--provider-english` с подтверждённым EN провайдера или `--review-bindings` с явно проверенным `key -> englishFingerprint`. RU-only refresh не считается такой проверкой. Управляемый результат нельзя передавать в качестве `--previous-cache`.

```powershell
python tools/update_atm9_quests.py review `
  --fresh-author <new-pristine-author> `
  --upstream-lock <new-upstream-lock.json> `
  --published <published-source> `
  --published-snapshot <research>/published-inputs.json `
  --community-cache <research>/fresh-community.json `
  --out <research>/review
```

Этот шаг не выполняет сетевых запросов. Он принимает свежий declared author version без старого count/version gate. Неизвестные BASE/JAR остаются ошибкой, а stale/missing перевод становится очередью и штатным EN fallback. Неизвестный будущий формат locale создаёт review без text overlay и с явным `translationSkippedReason`; native author ресурсы сохраняются.

Результат:

| Файл | Назначение |
| --- | --- |
| `overlay/` | Только локализованные native ресурсы и source-only dynamic profile/ownership/report |
| `required-lock-updates.json` | Точные original/new pins, BASE replacements, RU support/native-BASE роль, прежние support и предлагаемый narrow descriptor |
| `review-inputs.json` | SHA upstream lock, provider cache, физических инструментов/данных и fingerprint опубликованного снимка |
| `published-profile-snapshot.json` | Проверенный исходный published support/profile receipt |
| `review-result.json` | Краткий результат, coverage/staleness и состояние публикационного маршрута |
| `preserved-current/` | При неизменной текущей версии — побайтные прежние lock/tool/manifest для сверки сохранения |

Текущая 1.1.1 с прежними 108 ресурсами получает `mode: reuse-frozen-current-publication-profile`: остаются `8be48…` и `9ebb5…`, все runtime bytes/active validators/locks прежние. Отдельный dynamic schema2 review artifact не активируется. `applyBaseReplacementUpdates` в этом случае `false`.

Для нового профиля выдаётся `new-profile-requires-explicit-owner-data-integration`, точный `proposedDynamicQuestLocalization` и explicit BASE replacement rows. Поддерживаемый opt-in reader `atm9_quest_profile.py` уже принимает schema2: версия и число ресурсов берутся из нового upstream lock, без изменения кода под каждый выпуск. Владелец сначала независимо импортирует и проверяет новую авторскую сборку, затем принимает конкретные данные профиля и pins. Он привязывает каждую original-строку к **новому** BASE и обновляет только перечисленные locale/display pins и существующие notices. Никакого общего разрешения замены JAR нет. Дополнительные Modified JAR требуют самостоятельной совместимости новой авторской версии; перевод её не доказывает.

Дескриптор содержит ровно `schemaVersion: 2`, `kind: atm9-native-locale-display`, `sourceVersion`, `upstreamLockSha256`, `manifestPath`, `manifestSha256`, `patchTool`, `patchToolSha256`, `russianRole`. Пути профиля и patcher фиксированы; SHA approved patcher проверяется до импорта. `russianRole` равен `base`, если RU входит в новый авторский lock; `support`, если добавлен проверенный RU-файл; `absent`, если перевод не применён. `baseReplacements` должны точно совпадать с разрешёнными строками профиля. В Original это отдельная schema2-ветка `tools/portable-profile.json` с `questLocalization`; нынешняя schema1 и её bytes остаются прежними.

Штатный restore для schema2 использует `atm9_quest_restore.py`: проверяет точный новый upstream lock, принадлежность ATM9, явные source URL и hashes. Он допускает новый `clientFileId` и archive SHA без изменения старого importer, восстанавливает только отсутствующие закреплённые бинарные файлы и не ищет latest. Потерянные tracked author overrides или неизвестные JAR/config прерывают preflight до normalize и загрузок. Текущая schema1 продолжает использовать неизменённый importer. После выбора нового schema2 весь маршрут prepare/verify повторяется дважды и сравнивает effective bytes; публикация остаётся отдельным действием владельца.

Свежие реальные author RU и совместимые свежие community RU выше ручных fallback. Changed/new chapters с непроверенными inline spans остаются исходными и перечисляются в отчёте. Обновление сборки может выйти с частичным английским, не ожидая переписывания всех новых глав.

## Закреплённый повтор и CI

После review сохраните provider cache, manual/tool data, новый разрешённый профиль и lock pins в Git. Обычная CI выполняет только закреплённый restore/verify. **Не добавляйте refresh-provider в каждый build или запуск лаунчера.**

Если CI отдельно повторяет review для той же принятой операции, передайте её recipe:

```powershell
python tools/update_atm9_quests.py review `
  --fresh-author <same-pristine-author> --upstream-lock <same-upstream-lock.json> `
  --published <same-published-source> `
  --published-snapshot <same-published-inputs.json> `
  --community-cache <same-pinned-community.json> `
  --inputs-lock <accepted-review-inputs.json> --out <fresh-ci-review-directory>
```

Изменение любого входа отклоняется до записи. Для **новой** авторской версии или явного обновления перевода создаётся новый review/recipe; прежний recipe нельзя использовать как требование старого английского текста. Это проверка воспроизводимости одной операции, а не условие полноты перевода будущего релиза.

## Проверка настоящих текущих оболочек

```powershell
python tools/update_atm9_quests.py rehearse `
  --published <published-source> --published-snapshot <published-inputs.json> `
  --out <fresh-private-fixture> --cache <separate-private-cache> `
  --exercise-missing-base-jar
```

Команда делает независимую копию точных published content/tools/metadata без `.git`, мира или логов. Один известный BASE JAR сохраняется в exact-SHA cache и убирается только из этой копии. Затем **настоящая**, неизменённая `prepare_pack.py` / `restore_modified.py` запускается два раза. После каждого запуска весь published snapshot, включая legacy tool/manifest, support и JAR, должен совпасть побайтно. Пишутся полные native reports/stdout/stderr. Это не подменено отдельным тестом 107 spans и не заявляет клиентский runtime PASS.

На реальном текущем кандидате доказаны такие циклы Original и Modified, восстановление PigPen из точного кеша, повторная подготовка, EN/RU/107 spans byte equality и отказ настоящих оболочек от неизвестного конфига **до normalize** с сохранением конфига и всех 108 текстовых ресурсов.

Портативные unit-тесты используют только временные fixtures и committed source-only data. Они не ищут личные пути/AGENTS.md и не требуют старого числа глав/ключей в будущем авторском релизе:

```powershell
python -B -m unittest discover -s tools -p test_atm9_ru_future.py -v
python -B -m unittest discover -s tools -p test_update_atm9_quests.py -v
```
