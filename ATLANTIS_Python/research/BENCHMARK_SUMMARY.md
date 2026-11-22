# Benchmark summary

| Task | Evidence and best-supported conclusion |
|---|---|
| Certify all fixed-context iMC basins | Classical constant propagation certifies one global fixed point for 300 and 500 distinct gene loci. Sampling is unnecessary for this objective. |
| Discover rare ErbB basins | No rarity certification with the specified horizon and independent audit. SCC-guided discovery yielded slightly more distinct orbits in the pilot; general superiority is unestablished. |
| Transfer to epidermis | Initial-state encoding changes the result. With ordered levels and a zero-input context, both proposals discovered the same single cycle in this pilot. |
| Hardware speedup | None established. No new paid hardware jobs used. |

Raw experiment configurations, cycle words, ordered discovery sequences and audit counts are in results/transfer*.json. Basin sizes use the independent reference distribution. An orbit's appearance in a biased proposal cannot estimate its true mass.

### Follow-up with a longer horizon

For 99 independently audited rare ErbB targets under the fixed all-zero external input condition, fresh trials give an estimated 51 independent draws for a 95% chance of first discovery under the global bias mixture, 52 under the SCC mixture, and 109 under uniform sampling. Scrambled SCC requires an estimated 116. Estimates are specific to this frozen target set and condition. Analogous discovery of any genuinely rare attractor could include additional unlabelled outcomes. No quantum sampling advantage was tested or established by these classical controls.
