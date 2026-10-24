# DUP Protocol — краткая карточка (RU) · industrial pin

**Организация:** DUP Labs · **Продукт:** DUP Protocol · **Автор:** Уладзимир Дабранский (D.U.P.)  
**Дата:** 2026-10-24 · Полный вход (EN): [SHOWCASE.md](SHOWCASE.md) · EN one-pager: [ONE_PAGER.md](ONE_PAGER.md)  
**Репозиторий:** [`Gruver87/dup-protocol`](https://github.com/Gruver87/dup-protocol)  
**Front door (fund / audit):** [FUND_AUDIT_PREP.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/FUND_AUDIT_PREP.md)  
**ПВТ / HTP пакет:** [PVT_HTP_SHOW_PACK_RU.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/PVT_HTP_SHOW_PACK_RU.md)  
**CITATION:** [CITATION.cff](https://github.com/Gruver87/dup-protocol/blob/master/CITATION.cff) (1.3.1340)  
**Diligence brief:** [DILIGENCE_BRIEF.md](https://github.com/Gruver87/dup-protocol/blob/master/docs/DILIGENCE_BRIEF.md)  
**Канонический язык репозитория:** English. Этот файл — краткая карточка для показа / ПВТ. Обычным языком: [FOR_EVERYONE_RU.md](FOR_EVERYONE_RU.md).

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

- Tip-v2 48h (**TCP+TLS**): pack `375d14f`, тег [`v1.3.1339-tip-v2-industrial`](https://github.com/Gruver87/dup-protocol/releases/tag/v1.3.1339-tip-v2-industrial)  
- ADR 0020 Quick probe: `pin-libp2p-cutover-pending`. Окно 2026-10-08 — **VOID**, не PASS. Окно 2026-10-11 оборвалось ~44.2 ч, не PASS.  
- Pin libp2p STRICT 48h **PASS** (чистый git): pack [`pin-libp2p-strict-48h`](evidence/runs/pin-libp2p-strict-48h/) · окно **2026-10-18→20** · `hard_fails=0` · тег [`v1.3.1340-libp2p-industrial-mesh`](https://github.com/Gruver87/dup-protocol/releases/tag/v1.3.1340-libp2p-industrial-mesh). Не мейннет.  
- Предыдущий STRICT 2026-10-15–17 (грязный git) — архив `pin-libp2p-strict-48h-dirty-c1c281f`, не заменяет clean pack.  
- Bridge OFF + sprout labs verify — см. [FUND_READINESS.md](FUND_READINESS.md)

Long-Range и EVM STRICT Experimental — не доказательство пина.

---

## Что мы **не** заявляем

- Публичный audited mainnet / листинг токена  
- Готовый внешний security-audit PDF  
- Окна 2026-10-08 и 2026-10-11 как libp2p PASS  
- Prod Long-Range / включённый bridge  
- Зарегистрированный товарный знак НЦИС (есть только [prep](TRADEMARK_FILING_PREP_BY.md))  
- Юрлицо / email ПВТ в репозитории (поля-заглушки в NDA)  
- Автоматическое резидентство ПВТ / обязательность ИП этим документом

---

## IP / Беларусь

Авторское право + MIT: [IP_AND_ATTRIBUTION.md](IP_AND_ATTRIBUTION.md).  
Подготовка заявки на ТЗ в РБ (НЦИС): [TRADEMARK_FILING_PREP_BY.md](TRADEMARK_FILING_PREP_BY.md) — **не** свидетельство о регистрации.

---

## Просьба (ask)

Технический due diligence / грант / ПВТ: обзор **частной mesh + evidence packs**. Не «mainnet ready».  
Пакет для оценки «ИП / будущий резидент»: [PVT_HTP_SHOW_PACK_RU.md](PVT_HTP_SHOW_PACK_RU.md).

Демо pin: [DEMO_RUNBOOK_PIN.md](DEMO_RUNBOOK_PIN.md). FAQ (EN): [FAQ.md](FAQ.md). Контакт: GitHub [Gruver87](https://github.com/Gruver87).
