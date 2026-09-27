# Translation review findings — locales not auto-cleared

The 17 reviewed languages (de es it pt pt_BR fr ru nl zh_CN ja uk ca sv da
pl cs ko) had their `fuzzy` strings reviewed and cleared/rewritten directly (DeepSeek V4 Flash & Qwen 3.8 Flash).
The locales below were not fluent enough to auto-clear; findings are listed
for a native pass.

Detection is structural (a fuzzy string equal to a *different* confirmed UI
concept, or an accelerator the source declares but the translation drops),
so it cannot author the fix - a native must.


## sk
- Select All == '_Select' (dropped 'All')
- Select Odd == Select Even == 'Označené' (must differ)
- _Save dropped accelerator ('Uložiť')

## sl
- Invert selection == 'Cut selection'
- Crop selection == 'Copy selection'
- Select All == '_Select' (dropped 'All')
- Select Odd == Select Even == 'Izbrano' (must differ)
- _Save dropped accelerator ('Shrani')

## sr
- _Save dropped accelerator ('Сачувај')

## hr
- Invert selection == 'Cut selection'
- Crop selection == 'Copy selection'
- Select All == '_Select' (dropped 'All')
- Use the combined select and pan tool == rectangular tool
- Select Odd == Select Even == 'Odabrano' (must differ)
- _Save dropped accelerator ('Spremi')

## bg
- Invert selection == 'Cut selection'
- Crop selection == 'Copy selection'
- Select All == '_Select' (dropped 'All')
- Select Odd == Select Even == 'Избрано' (must differ)
- _Save dropped accelerator ('Запис')

## gl
- Invert selection == 'Cut selection'
- Select All == '_Select' (dropped 'All')
- Use the combined select and pan tool == rectangular tool
- Select Odd == Select Even == 'Seleccionado' (must differ)
- _Save dropped accelerator ('Gardar')

## eu
- Invert selection == 'Cut selection'
- Crop selection == 'Copy selection'
- Select All == '_Select' (dropped 'All')
- Use the combined select and pan tool == rectangular tool
- Select Odd == Select Even == 'Hautatua' (must differ)
- _Save dropped accelerator ('Gorde')

## oc
- Invert selection == 'Cut selection'
- Crop selection == 'Copy selection'
- Select All == '_Select' (dropped 'All')
- Select Odd == Select Even == '_Seleccionar' (must differ)
- _Save dropped accelerator ('Salvar')

## be
- Select Odd == Select Even == 'Выбраны' (must differ)
- _Save dropped accelerator ('Захаваць')

## af
- _Save dropped accelerator ('Stoor')

## tr
- Invert selection == 'Cut selection'
- Select All == '_Select' (dropped 'All')
- Select Odd == Select Even == 'Seçili' (must differ)
- _Save dropped accelerator ('Kaydet')

## el
- Invert selection == 'Cut selection'
- Crop selection == 'Copy selection'
- Select All == '_Select' (dropped 'All')
- Use the combined select and pan tool == rectangular tool
- Select Odd == Select Even == 'Επιλεγμένο' (must differ)
- _Save dropped accelerator ('Αποθήκευση')

## hu
- Select All == '_Select' (dropped 'All')
- Select Odd == Select Even == 'Kijelölt' (must differ)
- _Save dropped accelerator ('Mentés')

## fi
- Select All == '_Select' (dropped 'All')
- Select Odd == Select Even == 'Valittu' (must differ)
- _Save dropped accelerator ('Tallenna')

## he
- Invert selection == 'Cut selection'
- Crop selection == 'Copy selection'
- Select All == '_Select' (dropped 'All')
- Use the combined select and pan tool == rectangular tool
- _Save dropped accelerator ('שמור')

## ar
- _Save dropped accelerator ('حفظ')

## fa
- _Save dropped accelerator ('ذخیره')

## hi
- _Save dropped accelerator ('सहेजें')

## gu
- Invert selection == 'Cut selection'
- Crop selection == 'Copy selection'
- Select All == '_Select' (dropped 'All')
- Use the combined select and pan tool == rectangular tool
- _Save dropped accelerator ('સાચવો')

## vi
- _Save dropped accelerator ('Lưu')

## id
- _Save dropped accelerator ('Simpan')

## ro
- _Save dropped accelerator ('Salvează')

## The `%dMb free in %s.` entry

After review this `ngettext` string is the only plural. Its real state
across the un-reviewed locales (read from the `.po`, not tooling output):

- **Correctly filled, still `fuzzy`** - right number of forms, `%d` before
  `%s`; only awaits a native confirming wording:
  af bg el eu fi gl hr hu id ro sk sl sr vi.
- **Untranslated, correct empty form count** (clean English fallback):
  fa gu he oc.
- **Untranslated, form count topped up to `nplurals`** in this change:
  be (3), ar (6).
- **Genuine latent bugs - `fuzzy`-masked, NOT auto-fixable (native reword)**:
  - **hi**: uses `%s` before `%d`. Python's `%` cannot reorder args, so
    un-fuzzing as-is raises at runtime. Reword `%d`-first (or move the source
    to a named `%(free)s` format).
  - **tr**: uses C positional `%1$d`/`%2$s`, which Python's `%` rejects
    (`unsupported format character '$'`). Same fix.

`zh_CN` and `ja` had exactly these bugs and were fixed during fluent review.
`msgfmt --check` skips `fuzzy`, so `hi`/`tr` stay silent until un-fuzzied -
the one real landmine, and it is exactly two strings.
