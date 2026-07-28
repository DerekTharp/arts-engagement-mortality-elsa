---
title: |
  Checking that the weights worked: a tutorial on balance diagnostics for marginal structural models, using arts engagement and mortality in the English Longitudinal Study of Ageing
---

**Derek Tharp, PhD**

Department of Accounting & Finance, University of Southern Maine, Portland, ME, USA

ORCID: 0000-0002-5973-2586

Correspondence to: Dr Derek Tharp, University of Southern Maine, Portland, ME, USA; derek.tharp@maine.edu

Word count: {main_word_count} (main text, excluding abstract, tables, and references); abstract {abstract_word_count} words.

## Abstract

**Background** Many exposures in ageing research, including cultural attendance, physical activity and socialising, decline as function worsens. They are often frozen at baseline or adjusted for concurrent health; both approaches mishandle time-varying confounding affected by prior exposure. Marginal structural models (MSMs) use inverse-probability weights, but applied studies rarely show whether those weights achieved balance or use a diagnostic aligned with stabilisation.

**Methods** Using a worked example, receptive arts engagement and mortality in the English Longitudinal Study of Ageing (ELSA; reconstructed from public archives; N={n_baseline}; {n_deaths_baseline} deaths; {n_panel_intervals} person-wave intervals), we fitted a ladder of models from baseline-fixed to a stabilised IPTW-IPCW MSM. For both non-reference exposure categories, we assessed balance within prior-exposure strata and adjusted the standardised mean differences (SMDs) for age and baseline covariates retained by the stabilised numerator.

**Results** Freezing exposure at baseline gave a hazard ratio of {hr_bfcl_frequent} (frequent vs never); updating it each wave moved the estimate to {or_uwt_frequent}; the MSM gave {or_msm_frequent} ({ci_msm_frequent_lo} to {ci_msm_frequent_hi}). In the largest transition stratum, mean absolute adjusted SMD fell from {bal_freq_prior_infreq_adj_unw} to {bal_freq_prior_infreq_adj_wt} for frequent versus never and from {bal_infreq_prior_infreq_adj_unw} to {bal_infreq_prior_infreq_adj_wt} for infrequent versus never. Comparisons with only {n_freq_prior_never} or {n_never_prior_freq} person-waves in one cell retained larger residuals.

**Conclusion** Balance diagnostics for stabilised MSM weights should condition on the full numerator and report every exposure contrast. Here weighting improved balance in common transitions but not uniformly in sparse transitions; this qualifies the weighted estimate without resolving unmeasured confounding.

---

## Key messages

**What is already known on this topic**
Marginal structural models with inverse-probability weights are the standard tool for a time-varying exposure whose confounders are themselves affected by earlier exposure. Yet applied studies seldom report whether their weights achieved balance, and an unadjusted marginal standardised mean difference is not the target of a stabilised weight.

**What this study adds**
Working through arts engagement and mortality in ELSA, this tutorial shows how to build and check the weights. The diagnostic stratifies on prior-wave exposure, adjusts for the other numerator covariates and includes both exposure contrasts, revealing improvement in common transitions and residual imbalance in sparse ones.

**How this study might affect research, practice or policy**
Reporting numerator-conditioned balance should be routine when fitting stabilised marginal structural models. The diagnostic prevents a weighted estimate from being read as free of confounding and identifies the exposure histories for which measured balance remains uncertain.

---

## Introduction

A recurring problem in the epidemiology of ageing is that the exposure of interest is also a marker of health. Going to concerts, museums or the theatre, taking exercise, seeing friends: each requires mobility, cognition and energy, and each falls away as people become ill. When the outcome is death, the exposure and the outcome share a common cause, declining function, that changes over time. Estimating the effect of the exposure then requires handling *time-varying confounding affected by prior exposure*, the setting for which marginal structural models (MSMs) fitted by inverse-probability weighting were developed.^1,2^ Neither of the two conventional approaches handles it. Freezing the exposure at a baseline value misclassifies people who later stop participating as they decline. Updating the exposure but adjusting for concurrent health in an ordinary regression conditions on a variable that is itself a consequence of earlier exposure, which can introduce bias rather than remove it.^3,4^

The MSM is well described.^1,2,5^ Less well handled in practice is the step after fitting: showing that the weights did what they were meant to do. In point-exposure propensity-score analysis, authors routinely report standardised mean differences (SMDs) before and after weighting to demonstrate balance.^6^ For a time-varying exposure the analogous check is subtler, and two errors are common: reporting no balance diagnostic at all, or reporting the *marginal* SMD, which stabilised weights are deliberately not designed to remove. This tutorial addresses that gap. We take one applied example through the full sequence, fit the MSM, and then focus on the diagnostic: what balance means for a time-varying exposure, why it must condition on the stabilised numerator,^7^ and what the resulting picture does and does not license us to conclude.

The worked example concerns receptive arts engagement and mortality in the English Longitudinal Study of Ageing (ELSA), a biennial cohort of older adults in England. A widely cited analysis reported that participants who attended cultural venues every few months or more had about a third lower mortality over 14 years than those who never attended, adjusting for a broad set of baseline characteristics, with engagement measured once at baseline.^8^ A short critique in this journal used a negative-control outcome (adult height, which arts engagement should not cause) and found that engagement predicted height after the same adjustments, indicating that baseline adjustment did not fully absorb the social patterning of engagement.^9^ A related study by the original authors examined cultural engagement alongside physical and social factors as predictors of incident disability.^10^ Its primary Cox models used baseline exposures and covariates; a fixed-effects sensitivity analysis used repeated observations to address time-invariant confounding. Together, these studies motivate questions about exposure change, health-related confounding and what repeated-measures analyses can establish. Our aim is not to adjudicate the substantive association but to demonstrate how to fit and check a marginal structural model for an exposure that tracks health.

## Methods

### The example and the data

ELSA has interviewed a representative sample of adults aged {baseline_min_age} and over in England every two years since 2002.^8^ Receptive arts engagement was measured at each wave by two self-completion items, attendance at galleries or museums and at the theatre, concerts or opera, combined into the higher of the two frequencies and grouped as never, infrequent (once or twice a year or less), or frequent (every few months or more), matching the original classification.^8^ The outcome was all-cause mortality.

The mortality linkage used in the original analysis (National Health Service records) is not available to external researchers, so we reconstructed the endpoint from publicly archived ELSA files (UK Data Service studies 5050 and 8773), using interview-status transitions and end-of-life proxy interviews. This reconstruction captured {n_deaths_baseline} deaths against the {published_deaths} in the linked endpoint, a gap we treat as a limitation of the illustration rather than of the method (Discussion; Supplement §S7). The methodological points below do not depend on the completeness of the endpoint. Our baseline analytic sample was wave-2 respondents aged {baseline_min_age} or older with complete exposure and covariate data (N={n_baseline}). For the time-varying analyses we built a person-wave panel under monotone censoring: each person contributed intervals from wave 2 until the first wave at which they were not interviewed or did not complete the arts items, after which they were censored ({n_panel_intervals} intervals; {n_panel_deaths} deaths; Supplement §S1).

### The causal structure

Figure 1 is the directed acyclic graph. Arts engagement at wave *t* (*A~t~*) depends on time-varying health *L~t~* (mobility, cognition, depressive symptoms, chronic disease), which is itself affected by earlier engagement *A~t-1~* and predicts both later engagement and death (*Y*). *L~t~* is therefore simultaneously a confounder of the *A~t~*→*Y* relationship and a mediator on the *A~t-1~*→*Y* path.^3^ Conditioning on *L~t~* in an outcome regression blocks that mediating path and can open a collider path if *L~t~* and *Y* share unmeasured causes; not conditioning on it leaves confounding. Under correct models, positivity and the other identification assumptions, inverse-probability-of-treatment weighting (IPTW) aims to build a pseudo-population in which *L~t~* no longer predicts *A~t~* conditional on the numerator, allowing the exposure to be related to the outcome without concurrent adjustment for *L~t~*.^1,2^ Baseline determinants that the measured covariates do not capture (*U*, for example family cultural capital or childhood circumstances) remain a source of confounding that no reweighting of measured variables can remove, and are the substance of the negative-control critique.^9^

### A ladder of models

We fitted the sequence in Table 1 on a common sample so the specifications are comparable, using discrete-time proportional-hazards models (complementary log-log link, the discrete-time analogue of Cox regression,^11,12^ with the log of interval length as an offset for unequal spacing) unless stated. **(i)** A baseline-fixed model froze engagement at its wave-2 value, reproducing the original mortality design.^8^ **(ii)** A time-varying model updated engagement each wave but did not adjust for time-varying health. **(iii)** A conventional time-varying outcome model additionally adjusted for concurrent *L~t~*. Under the causal structure in Figure 1, this adjustment may block part of an earlier-exposure pathway or induce collider bias.^3,4^ **(iv)** The MSM used stabilised inverse-probability weights instead of concurrent outcome-regression adjustment. All models adjusted for the same baseline covariates (Supplement §S3). A supplementary continuous-time Cox model gave concordant estimates (Supplement §S3).

### Weights and their diagnosis

The treatment model was a multinomial logistic regression for three-category engagement given prior engagement, age, baseline covariates and time-varying health; the stabilised weight is the ratio of the predicted probability of the observed exposure from a numerator model (prior engagement, age, baseline covariates) to that from the denominator model (adding *L~t~*).^2^ Informative loss to follow-up was handled by stabilised inverse-probability-of-censoring weights from a logistic model for remaining observed.^1,2^ The combined weight was accumulated within person and truncated at the 1st and 99th percentiles (Supplement §S2). These weights entered the outcome model with cluster-robust standard errors.

Balance checks whether the treatment weights removed the exposure–confounder association that the denominator was intended to address. For a *stabilised* weight the target is conditional: the numerator deliberately retains associations between current exposure, prior exposure and baseline covariates.^2,7^ A raw marginal SMD can therefore remain large after weighting without indicating failure. Stratifying only on prior exposure is also incomplete when the numerator contains other covariates. Following Jackson's regression approach,^7^ we assessed each time-varying confounder within strata of *A~t-1~*. For each of the frequent-versus-never and infrequent-versus-never contrasts, we regressed the confounder on current exposure, age, age squared and the full baseline covariate set. The current-exposure coefficient, standardised by the unweighted pooled standard deviation for that contrast and stratum, was the adjusted SMD. We fitted the regression without weights and with cumulative IPTW-IPCW weights; thus, before-and-after values used the same scale (Figure 2; Table 2; full values in Supplement §S2).

### Ethics

ELSA holds ethical approval from the London Multi-Centre Research Ethics Committee (MREC/01/2/91). Data access was through the UK Data Service under standard academic licence; no additional approval was required for this secondary analysis.

## Results

### The ladder of estimates

Table 1 shows the sequence. Freezing engagement at baseline gave a hazard ratio of {hr_bfcl_frequent} ({ci_bfcl_frequent_lo} to {ci_bfcl_frequent_hi}) for frequent versus never on the panel. Updating engagement each wave moved the estimate to {or_uwt_frequent} ({ci_uwt_frequent_lo} to {ci_uwt_frequent_hi}). Between consecutive waves {transition_pct_change_min}–{transition_pct_change_max}% of participants changed category (Supplement §S4), confirming that a single baseline measure discards observed movement. Such movement is compatible with health-related exposure change but does not identify its mechanism. The conventional time-varying outcome model gave {or_naive_frequent} ({ci_naive_frequent_lo} to {ci_naive_frequent_hi}); the MSM gave {or_msm_frequent} ({ci_msm_frequent_lo} to {ci_msm_frequent_hi}). The estimates and confidence intervals were similar across the four panel specifications. That similarity does not establish that time-varying confounding was absent; balance must be examined directly.

**Table 1.** A ladder of models for arts engagement and mortality, estimated on the common monotone-censored person-wave panel ({n_panel_intervals} intervals; {n_panel_deaths} deaths). All are discrete-time proportional-hazards models (complementary log-log link) adjusting for the same baseline covariates (Supplement §S3); hazard ratios are directly comparable across rows. The full-sample baseline-fixed Cox model (N={n_baseline}; {n_deaths_baseline} deaths) and a continuous-time time-varying Cox model are reported in Supplement §S3.

{ladder_table_md}

### Did the weights work?

The stabilised weights were tight (mean {wt_mean}, effective sample size {ess} of {n_panel_intervals} person-waves; Supplement §S2), indicating limited weight variability. This is not itself evidence of balance. As an illustration, the raw marginal frequent-versus-never mean absolute SMD changed from {bal_raw_pooled_mean_unw} to {bal_raw_pooled_mean_wt} (Supplement §S2). That contrast mixes exposure histories and does not condition on the stabilised numerator, so it cannot determine whether the weights succeeded.

The numerator-conditioned diagnostic gives a more specific picture (Figure 2; Table 2). In the prior-infrequent stratum, which contained the largest transition cells for each contrast, mean absolute adjusted SMD fell from {bal_freq_prior_infreq_adj_unw} to {bal_freq_prior_infreq_adj_wt} for frequent versus never and from {bal_infreq_prior_infreq_adj_unw} to {bal_infreq_prior_infreq_adj_wt} for infrequent versus never. For the frequent-versus-never contrast, mean adjusted imbalance changed from {bal_freq_prior_never_adj_unw} to {bal_freq_prior_never_adj_wt} among those previously never and from {bal_freq_prior_freq_adj_unw} to {bal_freq_prior_freq_adj_wt} among those previously frequent. The corresponding infrequent-versus-never values were {bal_infreq_prior_never_adj_unw} to {bal_infreq_prior_never_adj_wt} and {bal_infreq_prior_freq_adj_unw} to {bal_infreq_prior_freq_adj_wt}.

**Table 2.** Numerator-conditioned covariate balance, stratified by prior-wave exposure. Mean absolute adjusted standardised mean difference across the {n_balance_confounders} time-varying confounders, before and after IPTW-IPCW weighting. The adjusted SMD is the current-exposure coefficient from a confounder-specific regression containing age, age squared and all baseline numerator covariates, divided by the unweighted pooled standard deviation. Group *n* is the count in the named non-reference category; never *n* is the comparison count. Per-covariate values are in Supplement §S2.

{balance_stratified_summary_md}

Weighting reduced adjusted imbalance substantially in the common prior-infrequent comparisons. The {bal_adjusted_n_above_threshold} adjusted SMDs that remained above {smd_imbalance_threshold} all occurred in boundary comparisons with only {n_freq_prior_never} current-frequent or {n_never_prior_freq} current-never person-waves; the largest residual was {bal_adjusted_max_wt}. These findings identify limited overlap and imprecision in specific histories. Their pattern is consistent with functional decline accompanying large changes in engagement, but a balance diagnostic cannot distinguish terminal decline from other reasons for exposure change. A genetic sensitivity analysis separately indicated residual social patterning not absorbed by the measured covariates (Supplement §S5). Neither near-identical outcome estimates nor improved measured balance establishes that unmeasured confounding has been removed.

## Discussion

This worked example makes a general point: an MSM estimate needs a diagnostic aligned with the weight numerator. The frequent-versus-never estimate moved from {hr_bfcl_frequent} when exposure was frozen at baseline to {or_uwt_frequent} when it was updated, and to {or_msm_frequent} after weighting. Those shifts alone do not reveal whether weighting addressed measured confounding. The numerator-conditioned diagnostic showed clear improvement in common transition cells and residual imbalance in sparse boundary cells, locating the histories for which the weighted contrast is least secure.

The distinction between marginal and numerator-conditioned balance is the practical message for analysts fitting these models.^7^ A stabilised weight is meant to remove only the exposure–confounder association that remains after conditioning on the numerator. A large marginal SMD after weighting is therefore not necessarily a sign of failure, and a smaller one is not evidence of success. If the numerator contains baseline covariates as well as exposure history, stratification on history alone remains insufficient; regression adjustment or finer stratification is required.^7^ Diagnostics should include every contrast for a categorical exposure, attach cell sizes and retain signed per-covariate values.

The diagnostics also sharpen what can be said about the substantive example. Freezing a health-tracking exposure at baseline,^8^ as in the mortality analysis, does not represent later changes observed in the panel. The related disability paper's primary Cox analysis likewise used baseline physical and social exposures, while its fixed-effects sensitivity analysis exploited repeated observations to address time-invariant confounding.^10^ Neither design is the concurrent-adjusted model fitted here as a tutorial step. The negative-control critique raised a distinct concern: residual baseline social patterning.^9^ Reweighting measured covariates cannot address that concern or unmeasured health change between biennial interviews. The balance check therefore qualifies the MSM association rather than resolving it.

The illustration has limits that bound its substantive reading. Its reconstructed endpoint captured {n_deaths_baseline} deaths against {published_deaths} in the linked data, and a two-dimensional bias analysis placed the full-sample estimate between about {uc_grid_min_hr} and {uc_grid_max_hr} across the prespecified scenarios (Supplement §S7). Only {n_panel_deaths} of the {n_deaths_baseline} baseline deaths fall inside the monotone-censored panel, and the low-variability censoring weights do not eliminate possible selection. Exposure is measured by two self-report items every two years, capturing frequency rather than depth of engagement and missing interim change. Sparse transition cells limit some conditional diagnostics. Regression-adjusted SMDs rely on the specified main-effect adjustment, summarise mean differences and do not guarantee full distributional balance. Survey weights were not applied, so estimates describe the analytic cohort rather than the English population. These limits constrain inference about arts engagement and mortality while leaving the diagnostic procedure available for better-linked and more frequently measured data.

---

## Declarations

**Data sharing:** Individual-level ELSA data are publicly available from the UK Data Service under standard academic licence (study 5050 for the harmonised core dataset; study 8773 for the genetic file used in the polygenic score sensitivity analysis). NHS-linked mortality records referenced by the original mortality analysis are not part of this public-data reconstruction; such linkage is currently available only to the ELSA team or through the UK Longitudinal Linkage Collaboration.

**Code availability:** The analysis code (sample build, panel construction, treatment and censoring weight models, outcome models, balance diagnostics, polygenic-score sensitivity analysis, and figures) is publicly available at https://github.com/DerekTharp/arts-engagement-mortality-elsa. It is implemented in Python (numpy, scipy, pandas, matplotlib), with the survival, discrete-time, marginal-structural-model, and ordered-logit estimators written directly on those libraries so no proprietary software is required; the original Stata pipeline is included as a reference implementation. Another researcher with UK Data Service access to studies 5050 and 8773 can edit one path and regenerate all tables and figures from raw data (Supplement §S8).

**Author contributions:** DT conceived the study, conducted all analyses, drafted the manuscript, and is the guarantor.

**Use of generative AI:** The author used Claude (Anthropic) to assist with improving the readability and language of the manuscript and analysis code. The author reviewed and edited all content and takes full responsibility for the published article. The author also used Codex (OpenAI) for code review, diagnostic-design checks and language editing during the final revision; all Codex-assisted changes were reviewed, the complete analysis was rerun and the source materials were verified by the author.

**Competing interests:** None declared.

**Funding:** This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.

**Patient and public involvement:** This secondary analysis of an established cohort study did not involve patients or members of the public in its design, conduct, or reporting.

---

## References

1. Robins JM, Hernán MA, Brumback B. Marginal structural models and causal inference in epidemiology. *Epidemiology* 2000;11:550-560. doi:10.1097/00001648-200009000-00011

2. Cole SR, Hernán MA. Constructing inverse probability weights for marginal structural models. *Am J Epidemiol* 2008;168:656-664. doi:10.1093/aje/kwn164

3. Robins JM. A new approach to causal inference in mortality studies with a sustained exposure period: application to control of the healthy worker survivor effect. *Math Modelling* 1986;7:1393-1512. doi:10.1016/0270-0255(86)90088-6

4. Naimi AI, Cole SR, Kennedy EH. An introduction to g methods. *Int J Epidemiol* 2017;46:756-762. doi:10.1093/ije/dyw323

5. Hernán MA, Robins JM. *Causal inference: what if*. Boca Raton: Chapman & Hall/CRC; 2020. Available at: https://miguelhernan.org/whatifbook

6. Austin PC, Stuart EA. Moving towards best practice when using inverse probability of treatment weighting (IPTW) using the propensity score to estimate causal treatment effects in observational studies. *Stat Med* 2015;34:3661-3679. doi:10.1002/sim.6607

7. Jackson JW. Diagnostics for confounding of time-varying and other joint exposures. *Epidemiology* 2016;27:859-869. doi:10.1097/EDE.0000000000000547

8. Fancourt D, Steptoe A. The art of life and death: 14 year follow-up analyses of associations between arts engagement and mortality in the English Longitudinal Study of Ageing. *BMJ* 2019;367:l6377. doi:10.1136/bmj.l6377

9. Wright L. Arts engagement, mortality and dementia: what can the data say? *J Epidemiol Community Health* 2020;74:764. doi:10.1136/jech-2020-214227

10. Fancourt D, Steptoe A. Comparison of physical and social risk-reducing factors for the development of disability in older adults: a population-based cohort study. *J Epidemiol Community Health* 2019;73:906-912. doi:10.1136/jech-2019-212372

11. D'Agostino RB, Lee ML, Belanger AJ, Cupples LA, Anderson K, Kannel WB. Relation of pooled logistic regression to time dependent Cox regression analysis: the Framingham Heart Study. *Stat Med* 1990;9:1501-1515. doi:10.1002/sim.4780091214

12. Prentice RL, Gloeckler LA. Regression analysis of grouped survival data with application to breast cancer data. *Biometrics* 1978;34:57-67. doi:10.2307/2529588

---

## Figure legends

**Figure 1.** Directed acyclic graph for a time-varying exposure that tracks health. *A~t~* = arts engagement at wave *t*; *L~t~* = time-varying health (mobility, cognition, depressive symptoms, chronic disease); *Y* = mortality; *V* = baseline covariates; *U* = unmeasured baseline social determinants. *L~t~* is at once a confounder of the *A~t~*→*Y* relationship and a mediator on the *A~t-1~*→*Y* path, the structure that requires inverse-probability weighting rather than outcome-regression adjustment.

**Figure 2.** Numerator-conditioned covariate balance before and after weighting. Rows show current frequent versus never and infrequent versus never; columns stratify by prior-wave exposure. Each point is the adjusted standardised mean difference for a time-varying confounder, obtained by regressing that confounder on the current-exposure contrast, age, age squared and the baseline covariates in the stabilised numerator, then dividing the exposure coefficient by the unweighted pooled standard deviation. Open circles are unweighted; filled circles are IPTW-IPCW weighted. Cell sizes are shown above each panel. Dashed lines mark ±{smd_imbalance_threshold}.
