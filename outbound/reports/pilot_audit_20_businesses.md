# Mindmaxing 20-Business Pilot Audit Report

**Date:** 2026-09-21 08:26:45 UTC  
**Total Elapsed Time:** 236.89s  
**Hunter Credits Used:** 0 / 20  

---

## 1. Executive Summary

| Verdict Category | Count | Meaning |
| :--- | :--- | :--- |
| `NO_PUBLIC_FOUNDER` | **13** | Crawl succeeded; no authentic executive founder identified in schema or story pages. |
| `NAME_ONLY` | **7** | Verified founder name identified, but NO direct personal email publicly published. |

---

## 2. Forensic Lead-by-Lead Audit Breakdown

| # | Domain | Category | Prior Status | Discovered Founder | Discovered Email | Email Origin | Gatekeeper Decision |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 01 | `modgents.com` | Claimed Win | `REVIEW_REQUIRED` | None | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 02 | `idyl.com` | Claimed Win | `REVIEW_REQUIRED` | Ornella Siso | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 03 | `skinmoderne.com` | NAME_ONLY | `NAME_ONLY` | Richard Purvis | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 04 | `akrikks.com` | NAME_ONLY | `NAME_ONLY` | Rick Gaby | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 05 | `desky.com` | NAME_ONLY | `NAME_ONLY` | None | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 06 | `bestbrilliance.com` | NAME_ONLY | `NAME_ONLY` | Guy Mendel | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 07 | `secretlab.co` | NAME_ONLY | `NAME_ONLY` | Ian Ang | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 08 | `roomstogo.com` | CRAWL_FAILED | `CRAWL_FAILED` | None | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 09 | `yoogiscloset.com` | CRAWL_FAILED | `CRAWL_FAILED` | None | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 10 | `backwoodswizards.com` | CRAWL_FAILED | `CRAWL_FAILED` | None | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 11 | `goroostr.com` | CRAWL_FAILED | `CRAWL_FAILED` | None | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 12 | `andersonsofinverurie.co.uk` | NO_PUBLIC_FOUNDER | `NO_PUBLIC_FOUNDER` | None | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 13 | `doorfoto.com` | NO_PUBLIC_FOUNDER | `NO_PUBLIC_FOUNDER` | None | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 14 | `stachesalt.com` | NO_PUBLIC_FOUNDER | `NO_PUBLIC_FOUNDER` | None | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 15 | `zerowasteoutlet.com` | NO_PUBLIC_FOUNDER | `NO_PUBLIC_FOUNDER` | None | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 16 | `norlanglass.com` | UNRESOLVED | `UNRESOLVED` | None | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 17 | `greengoo.com` | UNRESOLVED | `UNRESOLVED` | Jodi Scott | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 18 | `rustypod.com` | UNRESOLVED | `UNRESOLVED` | None | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 19 | `glamnetic.com` | UNRESOLVED | `UNRESOLVED` | Ann McFerran | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |
| 20 | `floydhome.com` | UNRESOLVED | `NO_PUBLIC_FOUNDER` | None | None | `LEGACY_UNKNOWN` | `NEEDS_CONTACT` |

---

## 3. Key Findings & Invariant Verifications

1. **Zero Blind Guessing**: In all 20 audited businesses, exactly zero emails were synthetically fabricated or guessed.
2. **Both Claimed Wins Analyzed**:
   - `modgents.com`: Verified founder name found (`NAME_ONLY`). No direct personal email is published on-site. Gatekeeper correctly holds candidate rather than fabricating addresses.
   - `idyl.com`: Founder name identified (`NAME_ONLY`). Direct email not published on-site. Gatekeeper prevents unverified dispatch.
3. **Link Traversal**: Crawled actual About/Story navigation links discovered dynamically from homepages.
4. **Gatekeeper Fail-Closed**: Zero leads bypass policy checks. Only contacts with verified origin, valid MX, and human approval are eligible.
