# DUP Protocol — краткая карточка (RU) · industrial pin

**Организация:** DUP Labs · **Продукт:** DUP Protocol · **Автор:** Уладзимир Дабранский (D.U.P.)  
**Дата:** 2026-10-07 · Полный вход (EN): [SHOWCASE.md](SHOWCASE.md) · EN one-pager: [ONE_PAGER.md](ONE_PAGER.md)  
**Репозиторий:** [`Gruver87/dup-protocol`](https://github.com/Gruver87/dup-protocol)  
**Канонический язык репозитория:** English. Этот файл — краткая карточка для показа / ПВТ. Обычным языком, без фонда: [FOR_EVERYONE_RU.md](FOR_EVERYONE_RU.md).

---

## Одной фразой

**DUP Protocol** — промышленный гибридный L1 (Python + Rust) с fail-closed частной prod-profile mesh-сетью, деньгами только в satoshi и evidence packs на диске. Два репозитория: **industrial pin** (заморозка аудита + working tip) и **Experimental** (R&D).

---

## Два репозитория

| | Pin (это дерево) | Experimental |
|---|-----|----------------|
| GitHub | [dup-protocol](https://github.com/Gruver87/dup-protocol) | [dup-protocol-experimental](https://github.com/Gruver87/dup-protocol-experimental) |
| Роль | Аудит-заморозка; tip-v2 TCP+TLS soak; working tip ADR 0020 libp2p | libp2p depth, Long-Range lab, EVM STRICT |
| Не путать | Pin packs (`375d14f`, `pin-libp2p-strict-48h`) | Long-Range и STRICT Experimental |

---

## Что доказано на pin

- Tip-v2 48h (**TCP+TLS**): pack `375d14f`, тег `v1.3.1339-tip-v2-industrial`  
- ADR 0020 Quick probe: `pin-libp2p-cutover-pending`. Окно 2026-10-08 — **VOID**, не PASS. Окно 2026-10-11 оборвалось на 44.2 ч, не PASS.
- Pin libp2p STRICT 48h **PASS**: `pin-libp2p-strict-48h` (15–17 октября 2026, `hard_fails=0`). Не мейннет. Тег не резался. Git на старте был грязный.
- Bridge OFF + sprout labs verify + Exp→pin merge honesty — см. [FUND_READINESS.md](FUND_READINESS.md)

Long-Range и EVM STRICT Experimental — не доказательство пина.

---

## Что мы **не** заявляем

- Публичный audited mainnet / листинг токена  
- Готовый внешний security-audit PDF  
- Окна 2026-10-08 и 2026-10-11 как libp2p PASS. Тег `v1.3.1340-libp2p-industrial-mesh` нарезан (не публичная mainnet)  
- Prod Long-Range / включённый bridge  
- Зарегистрированный товарный знак НЦИС (есть только [prep](TRADEMARK_FILING_PREP_BY.md))  
- Юрлицо / email ПВТ в репозитории (поля-заглушки в NDA)

---

## IP / Беларусь

Авторское право + MIT: [IP_AND_ATTRIBUTION.md](IP_AND_ATTRIBUTION.md).  
Подготовка заявки на ТЗ в РБ (НЦИС): [TRADEMARK_FILING_PREP_BY.md](TRADEMARK_FILING_PREP_BY.md) — **не** свидетельство о регистрации.

---

## Просьба (ask)

Технический due diligence / грант / ПВТ: обзор **частной mesh + evidence packs**. Не «mainnet ready».

Демо pin: [DEMO_RUNBOOK_PIN.md](DEMO_RUNBOOK_PIN.md). FAQ (EN): [FAQ.md](FAQ.md). Контакт: GitHub [Gruver87](https://github.com/Gruver87).
