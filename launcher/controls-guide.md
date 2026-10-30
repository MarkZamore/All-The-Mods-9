# Управление ATM9 Original

Пресет меняет только назначения клавиш по явной кнопке лаунчера. Язык игры, графика, дальности, звук и настройки микрофона сохраняются. Обычные движение, прыжок, приседание, бег, инвентарь и панель 1–9 остаются стандартными. Творческие save/load toolbar, социальное меню, spectator outlines и cinematic camera оставлены без отдельных клавиш.

Это общая раскладка. Независимые действия мира имеют разные физические кнопки без плотной сетки сочетаний Shift/Ctrl/Alt. Нативный Forge при одновременном удержании нескольких модификаторов может активировать несколько их назначений, поэтому такой способ расширить боевую клавиатуру здесь не используется.

Сохранены исходные GUI-клики/редактирование и авторские движения/прыжки/подсказки, привязанные к тем же кнопкам. Эти существующие пары не объявляются удалёнными: экран управления может по-прежнему отмечать контекстные или намеренно совместные назначения красным. Проверка относится к независимым действиям мира, а не к обещанию нуля всех красных строк.

## Основные назначения

| Действие | Кнопка |
| --- | --- |
| Toggle Magnet (`simplemagnets.keys.toggle`) | f10 |
| Open Wireless Universal Grid (`key.universalgrid.openWirelessUniversalGrid`) | Num subtract |
| Change Radial Mining Mode (`key.apotheosis.toggle_radial_mining`) | Page Down |
| Open Satchel (`key.occultism.backpack`) | Num 6 |
| Open Storage Accessor (`key.occultism.storage_remote`) | Num 7 |
| iris.keybind.reload (`iris.keybind.reload`) | f6 |
| iris.keybind.toggleShaders (`iris.keybind.toggleShaders`) | f8 |
| iris.keybind.shaderPackSelection (`iris.keybind.shaderPackSelection`) | O |
| Open Backpack (`keybind.sophisticatedbackpacks.open_backpack`) | B |
| Open Super Wireless Grid (`key.rebornstorage.openWirelessCraftingGrid`) | Num divide |
| Open Tempad screen (`key.tempad.shortcut`) | Num 9 |
| Cataclysm Ability (`key.cataclysm.ability`) | X |
| Cataclysm Helmet Ability (`key.cataclysm.helmet_ability`) | ; |
| Cataclysm Chestplate Ability (`key.cataclysm.chestplate_ability`) | ' |
| Cataclysm Boots Ability (`key.cataclysm.boots_ability`) | правый Alt |
| Toggle Light Overlay (`key.moreoverlays.lightoverlay.desc`) | f7 |
| Toggle Chunk Boundaries (`key.moreoverlays.chunkbounds.desc`) | f9 |
| Pick Up (`key.easy_villagers.pick_up`) | delete |
| Zoom (`justzoom.keybinds.keybind.zoom`) | Mouse 4 |
| Toggle Engine (`keybind.ironjetpacks.engine`) | J |
| Toggle Hover Mode (`keybind.ironjetpacks.hover`) | H |
| Open/Close Curios Inventory (`key.curios.open.desc`) | G |
| Open Spell Wheel (`key.irons_spellbooks.spell_wheel`) | R |
| Cast Selected Spell (`key.irons_spellbooks.spellbook_cast`) | V |
| Open Backpack (`key.travelersbackpack.inventory`) | Num 5 |
| Swap Tool/Change Hose Mode (`key.travelersbackpack.cycle_tool`) | backspace |
| Item Mode Switch (`key.mekanism.mode`) | K |
| Module Tweaker (`key.mekanism.module_tweaker`) | \ |
| Pneumatic Armor General Options (`pneumaticcraft.armor.options`) | home |
| (Spell Book) Open Book (`key.ars_nouveau.open_book`) | C |
| Head Curio Menu (`key.ars_nouveau.head_curio_hotkey`) | Num 0 |
| Open/Close Accessories Inventory (`key.aether.open_accessories.desc`) | insert |
| Toggle Invisibility (`key.aether.invisibility_toggle.desc`) | 0 |
| Psi Master Keybind (`psimisc.keybind`) | Num 1 |
| FTB Ultimine (`key.ftbultimine`) | левый Alt |
| Search Nearby Inventories For Items (`key.findme.search`) | Y |
| Open Quests (`key.ftbquests.quests`) | Ё / grave accent |
| Tool Config (`key.draconicevolution.tool_config`) | . |
| Tool Modules (`key.draconicevolution.tool_modules`) | , |
| Focus Schematic Overlay (`create.keyinfo.toolmenu`) | menu |
| Access Nearby Toolboxes (`create.keyinfo.toolbelt`) | Caps Lock |
| Open Block Rotation Menu (`create.keyinfo.rotate_menu`) | Scroll Lock |
| Zoom In (`key.journeymap.zoom_in`) | = |
| Zoom Out (`key.journeymap.zoom_out`) | − |
| Create Waypoint (`key.journeymap.create_waypoint`) | N |
| Show / Hide Fullscreen Map (`key.journeymap.map_toggle_alt`) | M |
| Draw Mahoujin (`key.drawMahoujin`) | Num 2 |
| Change Mystic Code (`key.changeMysticCode`) | Num 4 |
| Selective Displacement (`key.selectiveDisplacement`) | Num 3 |
| Armor Hover Toggle (`gtceu.key.armor_hover`) | end |
| Enable Jetpack (`gtceu.key.enable_jetpack`) | Page Up |
| Swap Tool (`key.toolbelt.open`) | Num 8 |
| Open Wireless Terminal (`key.ae2.wireless_terminal`) | Num add |
| Open Wireless Crafting Grid (`key.refinedstorageaddons.openWirelessCraftingGrid`) | Num multiply |

Num означает цифровой блок. Mouse 4/5 — боковые кнопки мыши; Menu — клавиша контекстного меню. Для клавиатуры без этих кнопок выберите свои назначения соответствующих действий. Основные WASD, E, карта M, рюкзак B, квесты на Ё/grave accent и Curios G цифрового блока не требуют.

## Что требует самостоятельного выбора

В таблице назначены основные книги/колёса заклинаний, четыре способности Cataclysm, Mahou/Psi, основные средства полёта, хранения и инструменты. Прямые quick-cast слоты, отдельные режимы прочей брони/оружия, дополнительные фамильяры и редкие команды остаются без назначения. Если нужное действие не имеет другой доступной команды, ему нужна собственная клавиша; отсутствие назначения не выдаётся за полностью настроенную механику.

Точные исходные назначения всех строк доступны в `tools/keybinds/stock.json`: поля `nativeValue` и `defaultValue`, рядом название и категория. Нужную кнопку можно выбрать или сбросить в обычном меню управления; общий сброс вернёт исходные межмодовые пересечения.

## Источник и границы проверки

Файл содержит 488 имён: 159 назначены, 329 свободны. 83 независимых ванильных/мировых назначений используют разные физические кнопки. GUI и неизменённые авторские спутники ввода учитываются отдельно. Все 431 JAR закреплены полными SHA256 в stock.json; их байты этим пресетом не изменяются.

488 имён Original получены по точной принадлежности BASE/vanilla из наблюдавшегося реестра Modified. Все 431 BASE JAR побайтно совпадают с Original. Отдельный текущий Original-only реестр этим не объявляется измеренным.

Штатный парсер/Apply/Evaluate лаунчера прошёл девять проверок сохранности личных параметров, CRLF, чужих назначений и повторного применения. Native Forge 47.4 принял все 488 значений, а настоящий KeyMapping.same проверил все 3403 пар независимых мировых назначений: ноль конфликтов. Исходные GUI/спутники этим тестом не объявляются свободными от всех красных пересечений.

Реальное применение в запущенном клиенте с закрытием и повторным запуском ещё не подтверждено; работа каждой способности отдельно не испытана. DefaultSettings и его авторский файл 214 клавиш не заменяются. Forge после его загрузки повторно читает личные key_ строки; фактическое удержание пресета после закрытия/перезапуска остаётся отдельной проверкой.

Проверка данных: `python tools/keybinds/check_preset.py`. Для проверки только файлов пресета без установленных JAR: добавьте `--skip-jar-check`.
