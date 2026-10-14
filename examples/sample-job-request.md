# Sample research request (ILLUSTRATIVE)

**You type:**
```
/research Find recurring-revenue B2B service opportunities for restaurants that a solo founder could start with under $15k. US, no software development.
```

**The orchestrator then:**
1. Reads the config and checks for duplicate jobs. None found, so it creates `JOB-20261014-restaurant-b2b-services`.
2. Plans tasks 01–11 (see the `research` skill). It keeps task 07 (ai-tools-automation), because operating cost matters for a solo founder.
3. Runs 01, then 02. Then it launches 03, 04, 05 and 06 together (4 parallel), and then 07. Then 08, 09, 10 and 11.
4. Replies with the ranking, the counts, the Skeptic's main challenges and a link to `report.md`.
