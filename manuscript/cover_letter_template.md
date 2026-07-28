Derek Tharp, PhD\
Department of Accounting & Finance\
University of Southern Maine\
derek.tharp@maine.edu\
ORCID: 0000-0002-5973-2586

27 July 2026

Dr Anna Pearce\
Joint Editor-in-Chief\
Journal of Epidemiology and Community Health

Dear Dr Pearce,

Thank you for your letter of 24 June 2026 concerning manuscript jech-2026-226788, and for the invitation to resubmit as a Theory and Methods paper. The guidance was specific and constructive, and I have followed it closely. I enclose a substantially rewritten manuscript, "Checking that the weights worked: a tutorial on balance diagnostics for marginal structural models, using arts engagement and mortality in the English Longitudinal Study of Ageing", recast as a Theory and Methods tutorial, with a point-by-point account below of how each request has been addressed.

**Balance diagnostics conditioned on the stabilised numerator.** This is now the centrepiece of the paper. New Figure 2 and Table 2 present adjusted standardised mean differences for every time-varying confounder before and after weighting, within each stratum of prior-wave exposure (A~t-1~), for both frequent-versus-never and infrequent-versus-never engagement; the signed per-covariate values are in Supplement §S2. Because the stabilised numerator also contains age and baseline covariates, the diagnostic uses Jackson's regression approach to condition on those terms rather than stratifying on prior exposure alone. Weighting reduced mean adjusted imbalance from {bal_freq_prior_infreq_adj_unw} to {bal_freq_prior_infreq_adj_wt} and from {bal_infreq_prior_infreq_adj_unw} to {bal_infreq_prior_infreq_adj_wt} in the largest transition stratum. Residual values above the prespecified threshold were confined to sparse boundary comparisons containing only {n_freq_prior_never} or {n_never_prior_freq} person-waves in one cell. The revised conclusion is correspondingly precise: balance improved where transitions were well represented, remained uncertain in sparse histories, and does not rule out unmeasured social patterning or interim health decline.

**Reframing as a tutorial.** The manuscript now walks the reader through the problem, time-varying confounding affected by prior exposure when the exposure tracks health, through a ladder of models (baseline-fixed, time-varying, concurrent-adjusted, marginal structural model) to the construction of the weights and, in most detail, to their diagnosis. It conforms to the Theory and Methods specifications: {main_word_count} words of main text, a {abstract_word_count}-word structured abstract, {display_count} display items (a directed acyclic graph, the model ladder, and the two balance items), and {reference_count} references.

**No assumed prior knowledge; standalone abstract.** Every reference to the source studies now carries a one-clause description of what it did, and the abstract has been rewritten to read on its own without any prior knowledge of them. The three motivating studies are introduced through their actual designs: a baseline mortality analysis, a negative-control critique and a disability analysis with a repeated-observation sensitivity check. They are illustrations of general methodological questions, not objects of critique.

**The related Fancourt paper in this journal.** I now cite Fancourt and Steptoe's cohort study of physical and social factors associated with disability (J Epidemiol Community Health 2019;73:906–912). The manuscript accurately distinguishes its primary Cox analysis, which used baseline exposures and covariates, from its fixed-effects sensitivity analysis using repeated observations. It is discussed as motivation for asking what baseline and repeated-measures designs can establish, not as an instance of the concurrent-adjusted model fitted as a tutorial step. The reflection on previously published work is offered in the collegial spirit your journal encourages.

The canonical Python analysis and reporting pipeline, together with the Stata reference scripts, including the numerator-conditioned balance diagnostic and its plot, is publicly available at https://github.com/DerekTharp/arts-engagement-mortality-elsa, and a STROBE checklist accompanies the submission. The manuscript has not been published or submitted elsewhere. I have no competing interests and received no funding for this work.

I am grateful for the opportunity to revise, and I hope the strengthened diagnostics address the concerns you raised. I look forward to your assessment.

Sincerely,

Derek Tharp, PhD
