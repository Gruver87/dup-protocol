# Пакет для показа ПВТ / HTP — DUP Protocol

**Версия пакета:** 2026-10-24 (rev. 2 — ссылки, packs, ADR, ОКЭД-подсказка, HEAD)  
**Pin HEAD (снимок пакета):** `1a1059f8` · после merge этого файла см. `git log -1 -- docs/PVT_HTP_SHOW_PACK_RU.md`  
**Канон:** industrial pin [`Gruver87/dup-protocol`](https://github.com/Gruver87/dup-protocol)  
**R&D sibling:** [`Gruver87/dup-protocol-experimental`](https://github.com/Gruver87/dup-protocol-experimental)  

**Для кого:** эксперт / сотрудник ПВТ (HTP), который оценивает, похожа ли линия на будущую резидентскую ИТ/R&D-деятельность и имеет ли смысл автору дальше оформлять ИП / юрлицо.  
**Не является:** юридической консультацией, заявкой в ПВТ, бизнес-планом, инвестиционным меморандумом, обещанием резидентства или «mainnet ready».  
**Другие репозитории автора в этот пакет не входят.**

---

## 1. Карточка заявителя / продукта (фактшит)

| Поле | Значение |
|------|----------|
| Автор | Уладзимир Дабранский (Uladzimir Dabranski, D.U.P.) |
| Организация (лицо проекта) | **DUP Labs** — R&D / diligence face (не замена выписке ЕГР) |
| Продукт | **DUP Protocol** — гибридный L1 (Python-оркестрация + Rust/PyO3 hot path) |
| Публичный код | MIT · pin + experimental на GitHub |
| Юрформа / email ПВТ в репо | **Не заполнены** (placeholders) — см. [FIRM_NDA_OUTLINE.md](FIRM_NDA_OUTLINE.md) |
| Товарный знак РБ (НЦИС) | Только **prep** заявки — [TRADEMARK_FILING_PREP_BY.md](TRADEMARK_FILING_PREP_BY.md), **не** свидетельство |
| Внешний security audit PDF | **Нет** (prep / tracker; 2 пункта firm-owned открыты) |

---

## 2. Одной фразой

**DUP Protocol** — промышленная R&D-линейка частной fail-closed mesh-сети с доказательствами на диске (gates + 48h soak packs). Готова к **техническому due diligence**, не к заявлению публичного audited mainnet и не к листингу токена.

---

## 3. Два репозитория (намеренно)

| | Industrial pin | Experimental |
|---|---|---|
| GitHub | [dup-protocol](https://github.com/Gruver87/dup-protocol) | [dup-protocol-experimental](https://github.com/Gruver87/dup-protocol-experimental) |
| Роль | Аудит-заморозка + working tip; продуктовая линия для фирмы / ПВТ | Песочница: глубина libp2p, Long-Range **lab**, EVM STRICT |
| Доказательства для ПВТ | **Ключевые packs этого дерева** (см. ниже) | R&D-ёмкость; **не** подменять ими pin PASS |
| Транспорт | Freeze-tag era: TCP+TLS · working tip: rust-libp2p (ADR 0020) | libp2p / labs по своим packs |

**Ключевые pin packs (куда смотреть сразу):**

| Pack | Что это | Ссылка |
|------|---------|--------|
| `375d14f` | Tip-v2 48h soak PASS, TCP+TLS, тег `v1.3.1339-tip-v2-industrial` | [`docs/evidence/runs/375d14f/`](evidence/runs/375d14f/) |
| `pin-libp2p-strict-48h` | Libp2p STRICT 48h PASS (чистый git, 2026-10-18→20), тег `v1.3.1340-libp2p-industrial-mesh` | [`docs/evidence/runs/pin-libp2p-strict-48h/`](evidence/runs/pin-libp2p-strict-48h/) |
| `pin-libp2p-cutover-pending` | Quick probe + VOID 2026-10-08 (не PASS) | [`docs/evidence/runs/pin-libp2p-cutover-pending/`](evidence/runs/pin-libp2p-cutover-pending/) |

Полный реестр: [EVIDENCE_MATRIX.md](EVIDENCE_MATRIX.md).

---

## 4. Что доказано на pin (с id пакета)

| Утверждение | Доказательство | Не означает |
|-------------|----------------|-------------|
| Tip-v2 private mesh 48h (TCP+TLS) | Pack `375d14f` · тег [`v1.3.1339-tip-v2-industrial`](https://github.com/Gruver87/dup-protocol/releases/tag/v1.3.1339-tip-v2-industrial) | Публичный mainnet |
| Working-tip libp2p cutover + Quick probe | `docs/evidence/runs/pin-libp2p-cutover-pending/` | 48h PASS сам по себе |
| Pin libp2p STRICT 48h **PASS** (чистый git) | Pack [`pin-libp2p-strict-48h`](evidence/runs/pin-libp2p-strict-48h/) · окно **2026-10-18→20** · `passed=true`, `hard_fails=0`, `git_dirty=false` · тег [`v1.3.1340-libp2p-industrial-mesh`](https://github.com/Gruver87/dup-protocol/releases/tag/v1.3.1340-libp2p-industrial-mesh) | Публичный mainnet / firm audit PDF |
| Предыдущий STRICT 15–17 окт. (грязный git) | Архив `pin-libp2p-strict-48h-dirty-c1c281f` | Не заменяет clean pack |
| Окно 2026-10-08 | **VOID** (power-off) | Не PASS |
| Окно 2026-10-11 | Оборвано ~44.2 ч | Не PASS |
| Fail-closed money (satoshi integers) | Units + `industrial_gate` | Токен на бирже |
| Bridge на live mesh | **OFF** by design | Bridge ON |

Gaps: [MAINNET_GAP_ANALYSIS.md](MAINNET_GAP_ANALYSIS.md).

---

## 5. Стек и инженерия (для оценки «это ИТ / R&D?»)

| Слой | Содержание |
|------|------------|
| Языки | Python (оркестрация, API, политика P2P) + Rust/PyO3 (`abs_native`: crypto, state roots, RocksDB, EVM kernels) |
| Сеть | 3-node prod-profile mesh, chain id `778888` |
| Качество | CI, `industrial_gate`, probe/soak runbooks; **ADR** (Architecture Decision Records) — короткие записки «почему так» в [`docs/adr/`](adr/); на prod включены решения линейки **0001–0022**, кроме **0017** (Long-Range) и **0022** (council) — они **выключены** на боевом профиле |
| Деньги | Только целые satoshi; float на критическом пути отвергается |
| Лицензия | MIT (код открыт) · бренд DUP Labs / DUP Protocol MIT **не** передаёт |

Архитектура: [ARCHITECTURE.md](ARCHITECTURE.md) · видение: [VISION.md](VISION.md).

---

## 6. Сигналы для ПВТ vs чего в репо нет

| Вопрос ПВТ | Ответ репозитория |
|------------|-------------------|
| Есть ли свой программный продукт? | Да — DUP Protocol, публичный исходник |
| Есть ли R&D-дисциплина (доказательства, а не слайды)? | Да — evidence packs + gates |
| Разделена ли «продуктовая» и «опытная» линия? | Да — pin / experimental |
| Зарегистрировано ли юрлицо / ИП в репо? | **Нет** — только бренд-лицо DUP Labs |
| Подан ли ТЗ в НЦИС? | **Нет** — есть prep-чеклист |
| Есть ли внешний audit PDF? | **Нет** |
| Подходит ли под коды деятельности резидента ПВТ? | **Решает ПВТ** по своим регламентам. Ниже — **рабочая гипотеза автора для обсуждения**, не зарегистрированный ОКЭД и не одобрение ПВТ |

**Рабочая гипотеза ОКЭД (на подтверждение ПВТ / юристу, не claim):**

| Код (ОКЭД/ОКВЭД-подобная логика) | Смысл | Почему кажется уместным для DUP |
|----------------------------------|--------|----------------------------------|
| **62.01** | Разработка компьютерного ПО | Публичный гибридный L1: Python + Rust, mesh, gates |
| **72.19** | Прочие НИОКР в области естественных / технических наук | Industrial R&D: soak packs, ADR, fail-closed labs |

Просим ПВТ / юриста **подтвердить или скорректировать** коды под актуальный классификатор и режим резидентства. В git классификаторов резидентства нет.

---

## 7. Чего нельзя говорить после этого пакета

- «Уже резидент ПВТ» / «гарантия вступления» / «ИП обязателен этим файлом»  
- «Публичный audited mainnet» / «токен листится»  
- «Товарный знак уже зарегистрирован в НЦИС»  
- «Experimental STRICT = pin industrial PASS»  
- «Окна 2026-10-08 или 2026-10-11 — это libp2p PASS»  
- «Коды 62.01 / 72.19 уже утверждены ПВТ» — нет, только гипотеза для диалога  
- Любые сторонние репозитории автора как часть DUP Protocol

---

## 8. Порядок показа (рекомендуемый)

Прямые ссылки на GitHub (pin `master`):

### 15 минут

1. [FOR_EVERYONE_RU.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/FOR_EVERYONE_RU.md) — границы простым языком  
2. Этот файл: [PVT_HTP_SHOW_PACK_RU.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/PVT_HTP_SHOW_PACK_RU.md)  
3. [ONE_PAGER_RU.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/ONE_PAGER_RU.md)  
4. [AT_A_GLANCE.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/AT_A_GLANCE.md)  

В репозитории те же пути: `docs/FOR_EVERYONE_RU.md`, `docs/ONE_PAGER_RU.md`, `docs/AT_A_GLANCE.md`.

### 45–60 минут (diligence)

5. [DILIGENCE_BRIEF.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/DILIGENCE_BRIEF.md) · [FUND_AUDIT_PREP.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/FUND_AUDIT_PREP.md)  
6. [EVIDENCE_MATRIX.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/EVIDENCE_MATRIX.md) + packs [`375d14f`](https://github.com/Gruver87/dup-protocol/tree/master/docs/evidence/runs/375d14f) и [`pin-libp2p-strict-48h`](https://github.com/Gruver87/dup-protocol/tree/master/docs/evidence/runs/pin-libp2p-strict-48h)  
7. [MAINNET_GAP_ANALYSIS.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/MAINNET_GAP_ANALYSIS.md)  
8. [IP_AND_ATTRIBUTION.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/IP_AND_ATTRIBUTION.md) · [TRADEMARK_FILING_PREP_BY.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/TRADEMARK_FILING_PREP_BY.md)  
9. По желанию live: [DEMO_RUNBOOK_PIN.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/DEMO_RUNBOOK_PIN.md) · [FUND_DEMO_OPERATOR_PACK.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/FUND_DEMO_OPERATOR_PACK.md)  
10. Индекс: [SHOWCASE.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/SHOWCASE.md) · [FAQ.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/FAQ.md)

### Experimental (приложение, не замена pin)

- [SHOWCASE (experimental)](https://github.com/Gruver87/dup-protocol-experimental/blob/main/docs/SHOWCASE.md)  
- STRICT packs там — только R&D-ёмкость; для ПВТ-решения по продуктовой линии смотреть **pin**.

---

## 9. Как ПВТ может перепроверить сам (без доверия к слайду)

```text
git clone https://github.com/Gruver87/dup-protocol.git
cd dup-protocol
git rev-parse HEAD
# затем по VERIFY_SUITE / FUND_DEMO_OPERATOR_PACK:
# verify_project, industrial_gate, при поднятой mesh — probe_prod_mesh -Quick
# читать JSON/README внутри docs/evidence/runs/pin-libp2p-strict-48h/
# читать docs/evidence/runs/375d14f/
```

Детали: [VERIFY_SUITE.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/VERIFY_SUITE.md).

---

## 10. Что автору нужно вне git перед разговором об ИП / резидентстве

1. Заполнить контакты и выбрать форму (ИП / ООО) — сейчас placeholders.  
2. Сверить с ПВТ / юристом вид деятельности и коды (гипотеза §6: 62.01 / 72.19) под актуальный регламент.  
3. Опционально: подать ТЗ по prep НЦИС.  
4. Опционально: живое демо mesh.  
5. Следующий индустриальный шаг продукта: внешний audit PDF — усиливает diligence, **не** подменяет решение ПВТ по резидентству (и не требуется для этого диалога, если бюджета нет).

---

## 11. Ask к ПВТ (честный)

Просим **техническую оценку**:

1. Выглядит ли DUP Labs / DUP Protocol как устойчивая ИТ/R&D-линия, с которой разумно дальше оформлять хозяйственную деятельность и обсуждать путь к резидентству — на базе **частной mesh + evidence ledger**, без заявления «mainnet ready» и без обещания автоматического резидентства.  
2. Имеет ли смысл для дальнейшего оформления опираться на гипотезу видов деятельности **62.01** (разработка ПО) и **72.19** (НИОКР) — или ПВТ укажет более точные коды / иной путь.

Ответ «скорректируйте коды / пока рано для резидентства / линия выглядит как ИТ-R&D» — ожидаемый и полезный исход. Мы не просим одобрить статус этим письмом.
