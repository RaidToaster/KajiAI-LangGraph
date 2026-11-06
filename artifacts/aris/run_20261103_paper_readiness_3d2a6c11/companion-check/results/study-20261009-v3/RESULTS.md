# Completed KajiAI-LangGraph evaluation

**Complete: 500 full-workflow attempts and 500 model-only attempts on the same 500 AVeriTeC development claims.**

Failed attempts remain in the denominator. No different-source exploratory runs were pooled. These are local label-only results with contemporary web access, not official AVeriTeC evidence scores.

| Condition | Accuracy (95% Wilson interval) | Macro F1 | Coverage | Accuracy among covered outputs |
|---|---:|---:|---:|---:|
| majority_baseline | 61.0% (56.7% to 65.2%) | 0.189 | 100.0% | 61.0% |
| closed_book_predictions | 53.8% (49.4% to 58.1%) | 0.417 | 99.0% | 54.3% |
| first_round_prediction | 68.8% (64.6% to 72.7%) | 0.530 | 99.2% | 69.4% |
| full_predictions | 67.4% (63.2% to 71.4%) | 0.500 | 98.4% | 68.5% |
| full_failure_inclusive | 67.4% (63.2% to 71.4%) | 0.500 | 98.4% | 68.5% |
| structural_only | 9.0% (6.8% to 11.8%) | 0.086 | 10.0% | 90.0% |
| full_policy | 8.4% (6.3% to 11.2%) | 0.083 | 8.8% | 95.5% |

Paired workflow-minus-control accuracy: 13.60 percentage points; 95% paired bootstrap interval 8.60 to 18.60; exact two-sided McNemar p=1.3453156e-07.

Accepted-label accuracy interval: 84.9% to 98.7%; coverage interval: 6.6% to 11.6%. Accepted label counts: {"Refuted": 35, "Supported": 9}. Jev removed 6 structurally accepted outputs: 3 wrong and 3 correct labels.

Saved final-minus-first accuracy: -1.40 percentage points (95% bootstrap -4.00 to 1.20); on 492 nonfatal trajectories: -0.81 (-3.25 to 1.63). This is trajectory truncation, not a separately run one-round experiment.

Additional research: 62 changed predictions, 18 wrong-to-correct, 25 correct-to-wrong; 934 extra rounds, 263 without new ledger records; 1049 extra searches, 2013 extra fetch attempts, 23,546,637 extra observed tokens.

## Operational and citation measurements

### full_execution

```json
{
  "metric_scope": "Local label-only metrics, NOT the official AVeriTeC evidence score",
  "predictions": {
    "n": 500,
    "accuracy": 0.674,
    "macro_f1": 0.49996657082332174,
    "coverage": 0.984,
    "selective_accuracy": 0.6849593495934959,
    "per_class": {
      "Supported": {
        "precision": 0.7920792079207921,
        "recall": 0.6557377049180327,
        "f1": 0.7174887892376681,
        "support": 122
      },
      "Refuted": {
        "precision": 0.8787878787878788,
        "recall": 0.760655737704918,
        "f1": 0.8154657293497364,
        "support": 305
      },
      "Not Enough Evidence": {
        "precision": 0.20689655172413793,
        "recall": 0.17142857142857143,
        "f1": 0.1875,
        "support": 35
      },
      "Conflicting Evidence/Cherrypicking": {
        "precision": 0.19387755102040816,
        "recall": 0.5,
        "f1": 0.27941176470588236,
        "support": 38
      }
    },
    "confusion_matrix": {
      "Supported": {
        "Supported": 80,
        "Refuted": 5,
        "Not Enough Evidence": 6,
        "Conflicting Evidence/Cherrypicking": 29,
        "ABSTAIN": 2
      },
      "Refuted": {
        "Supported": 13,
        "Refuted": 232,
        "Not Enough Evidence": 17,
        "Conflicting Evidence/Cherrypicking": 38,
        "ABSTAIN": 5
      },
      "Not Enough Evidence": {
        "Supported": 4,
        "Refuted": 13,
        "Not Enough Evidence": 6,
        "Conflicting Evidence/Cherrypicking": 12,
        "ABSTAIN": 0
      },
      "Conflicting Evidence/Cherrypicking": {
        "Supported": 4,
        "Refuted": 14,
        "Not Enough Evidence": 0,
        "Conflicting Evidence/Cherrypicking": 19,
        "ABSTAIN": 1
      }
    }
  },
  "failure_inclusive_predictions": {
    "n": 500,
    "accuracy": 0.674,
    "macro_f1": 0.49996657082332174,
    "coverage": 0.984,
    "selective_accuracy": 0.6849593495934959,
    "per_class": {
      "Supported": {
        "precision": 0.7920792079207921,
        "recall": 0.6557377049180327,
        "f1": 0.7174887892376681,
        "support": 122
      },
      "Refuted": {
        "precision": 0.8787878787878788,
        "recall": 0.760655737704918,
        "f1": 0.8154657293497364,
        "support": 305
      },
      "Not Enough Evidence": {
        "precision": 0.20689655172413793,
        "recall": 0.17142857142857143,
        "f1": 0.1875,
        "support": 35
      },
      "Conflicting Evidence/Cherrypicking": {
        "precision": 0.19387755102040816,
        "recall": 0.5,
        "f1": 0.27941176470588236,
        "support": 38
      }
    },
    "confusion_matrix": {
      "Supported": {
        "Supported": 80,
        "Refuted": 5,
        "Not Enough Evidence": 6,
        "Conflicting Evidence/Cherrypicking": 29,
        "ABSTAIN": 2
      },
      "Refuted": {
        "Supported": 13,
        "Refuted": 232,
        "Not Enough Evidence": 17,
        "Conflicting Evidence/Cherrypicking": 38,
        "ABSTAIN": 5
      },
      "Not Enough Evidence": {
        "Supported": 4,
        "Refuted": 13,
        "Not Enough Evidence": 6,
        "Conflicting Evidence/Cherrypicking": 12,
        "ABSTAIN": 0
      },
      "Conflicting Evidence/Cherrypicking": {
        "Supported": 4,
        "Refuted": 14,
        "Not Enough Evidence": 0,
        "Conflicting Evidence/Cherrypicking": 19,
        "ABSTAIN": 1
      }
    }
  },
  "verified": {
    "n": 500,
    "accuracy": 0.084,
    "macro_f1": 0.08288055680287382,
    "coverage": 0.088,
    "selective_accuracy": 0.9545454545454546,
    "per_class": {
      "Supported": {
        "precision": 1.0,
        "recall": 0.07377049180327869,
        "f1": 0.13740458015267176,
        "support": 122
      },
      "Refuted": {
        "precision": 0.9428571428571428,
        "recall": 0.10819672131147541,
        "f1": 0.19411764705882353,
        "support": 305
      },
      "Not Enough Evidence": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "support": 35
      },
      "Conflicting Evidence/Cherrypicking": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "support": 38
      }
    },
    "confusion_matrix": {
      "Supported": {
        "Supported": 9,
        "Refuted": 0,
        "Not Enough Evidence": 0,
        "Conflicting Evidence/Cherrypicking": 0,
        "ABSTAIN": 113
      },
      "Refuted": {
        "Supported": 0,
        "Refuted": 33,
        "Not Enough Evidence": 0,
        "Conflicting Evidence/Cherrypicking": 0,
        "ABSTAIN": 272
      },
      "Not Enough Evidence": {
        "Supported": 0,
        "Refuted": 0,
        "Not Enough Evidence": 0,
        "Conflicting Evidence/Cherrypicking": 0,
        "ABSTAIN": 35
      },
      "Conflicting Evidence/Cherrypicking": {
        "Supported": 0,
        "Refuted": 2,
        "Not Enough Evidence": 0,
        "Conflicting Evidence/Cherrypicking": 0,
        "ABSTAIN": 36
      }
    }
  },
  "execution_error_rate": 0.016,
  "stop_reasons": {
    "max_rounds": 443,
    "evidence_sufficient": 44,
    "execution_error": 8,
    "stagnant_research": 5
  },
  "verification_statuses": {
    "insufficient_evidence": 448,
    "verified": 44,
    "execution_error": 8
  },
  "gap_counts": {
    "Establish source independence; copied reporting is not corroboration.": 357,
    "Each citation needs an exact quote from its retrieved text.": 353,
    "Citation support is uncertain for https://www.aninews.in/news/world/europe/183-pakistanis-living-illegally-in-france-including-ex-isi-chief-shuja-pashas-close-relative20201101081701/.": 1,
    "Find relevant evidence from at least two source hosts.": 35,
    "Leaked OPCW memos suggest the official report 'misrepresents the facts' and 'omitted significant material', while the OPCW Director General states the leaked documents are 'erroneous, uninformed, and wrong'.": 1,
    "Evidence confidence remains below High.": 71,
    "SANA claims reports are 'fabricated'; VOA/US Government claim SANA's accusation is 'false and misleading'.": 1,
    "Citation support is uncertain for https://www.democracynow.org/2019/5/23/leaked_opcw_report_raises_new_questions.": 1,
    "Lack of an independent, non-governmental scientific adjudication to resolve the conflict between Ian Henderson's 'manually placed' theory and the OPCW's 'air-dropped' conclusion.": 1,
    "This domain requires peer-reviewed evidence.": 27,
    "Lack of a verified official death toll of 'more than 225,000' specifically for October 29, 2020, in the provided records.": 1,
    "No supported verdict yet.": 37,
    "The Columbia University report provides a range (130k-210k) rather than the specific 160k figure mentioned in the claim.": 1,
    "Lack of a peer-reviewed medical journal or official health organization (e.g., CDC, WHO) that validates the '160,000 fewer dead' figure.": 1,
    "Resolve and cite the assertion: More than 225,000 people dead, 225,000. The estimates are, if we\u2019d have acted responsibly, there\u2019d be 160,000 fewer dead than there are today, because of covid-19.": 1,
    "The New York Times reports $750 in federal income taxes for 2016/2017, while the Trump Organization claims he paid 'tens of millions of dollars in personal taxes'.": 1,
    "No primary record of Trump using the exact phrase 'I know how to game the system' exists in the provided text.": 1,
    "No record contains the verbatim quote provided in the claim.": 1,
    "Resolve and cite the assertion: all those people that send in the phony ballots. \u2026 They want to have the count weeks after November 3.": 1,
    "Resolve and cite the assertion: You\u2019re watching the cheaters": 1,
    "Resolve and cite the assertion: You\u2019re watching the cheaters and all those people that send in the phony ballots. \u2026 They want to have the count weeks after November 3.": 1,
    "The claim asserts the growth is 'almost triple' the previous record, but evidence shows the previous record was 16.7%, making 33.1% approximately double.": 1,
    "A conflicting verdict requires cited evidence on both sides.": 8,
    "Resolve and cite the assertion: Donald Trump, when he thinks of climate change, he says hoax. Well, guess what? Speaking of hoaxes, remember what he said about these increasing violent hurricanes": 1,
    "Axios reports Trump suggested nuking hurricanes; Trump denies ever saying it.": 1,
    "Citation support is uncertain for https://abc7.com/post/surgeon-general-weighs-in-on-general-public-wearing-face-masks/6067977/.": 1,
    "Lack of consensus between observational studies and RCTs regarding community masking effectiveness.": 1,
    "Observational studies and public health guidance claim effectiveness in reducing spread, while the Cochrane systematic review of RCTs reports no clear reduction.": 1,
    "Citation support is uncertain for https://www.thehindu.com/news/national/Jammu-and-Kashmir-out-of-U.N.-list-of-disputes/article15687886.ece.": 1,
    "Citation support is uncertain for https://www.ndtv.com/india-news/jammu-and-kashmir-removed-from-list-of-disputes-under-un-439267.": 1,
    "GAO claims 'some success' in reducing volume via fencing, while CRS and UC San Diego research claims barriers primarily cause 'spatial redistribution' or 'displacement' without reducing overall volume.": 1,
    "Insufficient data specifically quantifying 'human smuggling' as a distinct metric from general 'illegal border crossings' in the provided records.": 1,
    "Lack of recent, comprehensive data (post-2020) that specifically isolates the impact of the newest 'bollard' style walls from other enforcement variables.": 1,
    "The National Academies report finds no evidence for cloth masks impeding aerosols, whereas other lab studies (e.g., JAMA, ScienceDirect) report cloth masks blocking 50-87% of particles.": 1,
    "Citation support is uncertain for https://www.sciencedirect.com/science/article/pii/S2352396424001920.": 1,
    "Lack of a standardized definition for 'meaningfully help' across the different study types (lab vs. observational vs. RCT).": 1,
    "Citation support is uncertain for https://jamanetwork.com/journals/jama/fullarticle/2776536.": 1,
    "Some citations were not retrieved.": 7,
    "Citation support is uncertain for https://cedmohub.eu/video-used-to-falsely-claim-protestors-torched-french-embassy-in-dr-congo/.": 1,
    "Citation support is uncertain for https://www.bbc.com/news/world-asia-54732525.": 1,
    "Citation support is uncertain for https://www.timesonline.com/story/news/politics/2020/06/20/fact-check-joe-biden-wants-to-eliminate-new-fracking-permits-not-all-fracking/112780366/.": 1,
    "Biden's statement 'I do rule out banning fracking' directly contradicts his debate response 'So am I' to Bernie Sanders' call to stop fracking as soon as possible.": 1,
    "The FDA states clinical trial data do not demonstrate effectiveness, while Bryant et al. conclude large reductions in deaths are possible.": 1,
    "Lack of high-certainty, large-scale Phase III trial data in the provided records to resolve the conflict between the Bryant et al. meta-analysis and the FDA/WHO determinations.": 1,
    "Insufficient data on specific dosage and timing across the conflicting studies to determine if efficacy is dependent on early administration.": 1,
    "Bryant et al. (2021) claims 'moderate-certainty evidence' for reduction in deaths, whereas the WHO claims evidence for mortality reduction is of 'very low certainty'.": 1,
    "Citation support is uncertain for https://www.usatoday.com/story/news/factcheck/2020/10/30/fact-check-donald-trump-jr-s-claim-flu-deaths-false/6055003002/.": 1,
    "The full autonomous internal terrorist list for the EU.": 1,
    "Resolve and cite the assertion: The United States, New Zealand, U.K., Australia": 1,
    "Citation support is uncertain for https://www.gov.uk/government/publications/proscribed-terror-groups-or-organisations--2/proscribed-terrorist-groups-or-organisations-accessible-version.": 1,
    "Resolve and cite the assertion: The United States, New Zealand, U.K., Australia, and the EU have not included the NDF in their official list of terrorist groups.": 1,
    "Resolve and cite the assertion: the EU have not included the NDF in their official list of terrorist groups.": 1,
    "The actual names of the 31 organisations listed by Australia.": 1,
    "Definition of 'NDF' to check for aliases (e.g., National Democratic Front).": 1,
    "Citation unrelated the finding: https://www.opensanctions.org/datasets/nz_designated_terrorists/.": 1,
    "Citation support is uncertain for https://www.state.gov/foreign-terrorist-organizations.": 1,
    "Citation support is uncertain for https://leadstories.com/hoax-alert/2020/10/fact-check-no-evidence-that-hunter-biden-is-dead.html.": 1,
    "Lack of longitudinal clinical trials tracking the incidence of staph infections in mask-wearers vs. non-mask-wearers.": 1,
    "Citation support is uncertain for https://link.springer.com/article/10.1186/s12982-026-02814-0.": 1,
    "Resolve and cite the assertion: Wearing face masks can cause infections from bacteria such as staphylococcus.": 1,
    "Absence of a definitive clinical study linking the bacterial load on masks directly to the onset of a staph infection in a controlled cohort.": 1,
    "Peer-reviewed discussion in PMC11649673 suggests contamination 'plausibly' leads to skin infection, whereas clinical experts in USA Today explicitly state masks 'do not cause staph infections'.": 1,
    "The manufacturer claims the flag has 'no politics involved,' while fact-checkers and critics argue it is inherently 'anti-Black Lives Matter' due to its association with the Blue Lives Matter counter-movement.": 1,
    "Citation support is uncertain for https://pmc.ncbi.nlm.nih.gov/articles/PMC10518292/.": 1,
    "Citation support is uncertain for https://www.medscape.com/viewarticle/932443.": 1,
    "Citation support is uncertain for https://www.cdc.gov/mis/hcp/clinical-overview/index.html.": 1,
    "Resolve and cite the assertion: Cutting the umbilical cord straight away deliberately denies the baby natural immunity so that medical professionals have a reason to vaccinate and medicate them.": 1,
    "The model did not return a valid evidence assessment.": 8,
    "Search for evidence against the proposed conclusion.": 8,
    "Every finding needs retrieved citations.": 8,
    "Citation support is uncertain for https://www.tommys.org/pregnancy-information/giving-birth/delayed-cord-clamping-optimal.": 1,
    "Citation support is uncertain for https://americanpregnancy.org/giving-birth/delayed-cord-clamping/.": 1,
    "Citation support is uncertain for https://www.acog.org/clinical/clinical-guidance/committee-opinion/articles/2020/12/delayed-umbilical-cord-clamping-after-birth.": 1,
    "Biden's debate quote 'We would make sure it's eliminated' contradicts his later statement 'I am not banning fracking.'": 1,
    "Biden's debate quote 'No more \u2014 no new fracking' contradicts his campaign's clarification that he only meant 'no new permits for oil and gas drilling on federal land and offshore.'": 1,
    "There is a tension between the 'Case Recovery Rate' (reported as 67.97% globally) and the 'Infection Fatality Rate' (estimated at 0.68%, implying >99% survival). This is explained in the text as a difference between confirmed cases (CFR/Recovery) and all infections including asymptomatic ones (IFR).": 1,
    "Lack of a single, peer-reviewed systematic review that establishes a definitive global 'recovery rate' (as opposed to IFR or CFR) for the entire population, as definitions of 'recovered' vary.": 1,
    "The Trump White House archives claim a 'lowest level in 25 years,' whereas FactCheck.org and Rappler cite EIA/EPA data showing emissions were lower in the early 1990s and 1970s-80s.": 1,
    "Citation support is uncertain for https://pmc.ncbi.nlm.nih.gov/articles/PMC9435423/.": 1,
    "Citation support is uncertain for https://nebraska.tv/news/local/grand-island-maintains-property-tax-rate-despite-county-increases.": 1,
    "Citation support is uncertain for https://politifact.com/factchecks/2020/oct/28/chris-jacobs/jacobs-charge-mcmurray-raised-taxes-grand-island-c/.": 1,
    "The Russian Foreign Ministry claims the cost was split 50/50, while a U.S. official claims the U.S. paid the full amount.": 1,
    "The Kremlin/Trump call the shipment 'humanitarian aid' and a 'gift', while the U.S. State Department calls it a 'purchase'.": 1,
    "Citation support is uncertain for https://www.nbcnews.com/politics/donald-trump/russian-plane-coronavirus-medical-gear-lands-u-s-after-trump-n1174436.": 1,
    "Citation support is uncertain for https://www.courthousenews.com/russia-sends-emergency-medical-aid-to-united-states/.": 1,
    "The Prime Minister and DWP claim the combination equals 80% of salary, whereas the BBC/IFS analysis demonstrates that many workers will receive less (e.g., 73%).": 1,
    "Some cited hosts repeat substantially similar text; verify original-source lineage.": 9,
    "Resolve and cite the assertion: UK Employees unable to work in tier 3 areas will get a combination of Job Support Scheme": 1,
    "One author warns 5G is unsafe, while another author in the same publication labels those warnings as 'scaremongering' and 'fringe views'.": 1,
    "Citation support is uncertain for https://www.sun-sentinel.com/2021/08/19/miami-cop-suspended-over-hand-gesture-hed-also-been-dinged-for-a-trump-campaign-mask/.": 1,
    "The specific text of the court order dated 16.12.2020 and the Declaration dated 19.12.2020 are missing, which would definitively prove if the NTA admitted the blunder.": 1,
    "News reports claim NTA corrected a result from 329 (fail) to 650 (topper), while NTA's official notification claims this specific scenario is 'fake' and 'fabricated'.": 1,
    "Citation support is uncertain for https://apnews.com/article/fact-checking-9582957367.": 1,
    "Resolve and cite the assertion: White House coronavirus adviser Dr. Anthony Fauci wrote a 2008 paper that found most 1918-1919 Spanish Influenza pandemic deaths were because of bacterial pneumonia from wearing masks.": 1,
    "Taiwan claims Chinese diplomats gate-crashed a private event; China claims they were in a public area.": 1,
    "Taiwan claims its official was assaulted; China claims its diplomat was assaulted.": 1,
    "Independent eyewitness testimony from non-diplomatic staff or hotel employees to resolve the conflicting accounts.": 1,
    "Different studies report different percentages of non-COVID excess deaths (17%, 26%, 33%) depending on the time window and methodology.": 1,
    "Resolve and cite the assertion: A third of excess deaths in the United States between 1 March": 1,
    "The full text or specific results of the Woolf et al. (JAMA 2020) study for the March-July/August period are missing; only a snippet stating it was 'partly explained' is available.": 1,
    "Resolve and cite the assertion: 1 August 2020 during the COVID-19 pandemic could not be directly attributed to the coronavirus": 1,
    "Citation support is uncertain for https://jamanetwork.com/journals/jama/fullarticle/2778361.": 1,
    "Citation support is uncertain for https://www.rollingstone.com/feature/anatomy-of-a-fake-news-scandal-125877/.": 1,
    "Philippine government sources (PNA, NTF-ELCAC, PCOO) claim the term was concocted by the CPP-NPA-NDF, while archival research and fact-checkers (Rappler, Vera Files, Altermidya) provide evidence of the term's use in the US and Canada prior to the CPP's founding.": 1,
    "Ruhm (2024) finds stringent restrictions decreased overall excess deaths, whereas the claim posits they increased non-COVID excess deaths.": 1,
    "Lack of a direct causal analysis specifically linking the policy of 'lockdowns' (as opposed to general pandemic fear or healthcare system strain) to non-COVID mortality causes in the US.": 1,
    "Stokes et al. suggest non-COVID excess deaths were primarily unrecognized COVID-19 deaths, whereas the claim attributes them to the lockdowns.": 1,
    "Resolve and cite the assertion: In the US lockdowns are partly responsible for excess deaths not directly attributed to COVID-19 which were observed in 2020.": 1,
    "Citation support is uncertain for https://www.latimes.com/politics/la-na-pol-2020-joe-biden-income-20190709-story.html.": 1,
    "Citation support is uncertain for https://www.usatoday.com/story/news/factcheck/2020/10/21/fact-check-biden-amassed-wealth-through-speaking-and-book-profits/5981003002/.": 1,
    "Citation support is uncertain for https://www.thequint.com/news/webqoof/aajtaks-claim-that-maskoor-usmani-hung-jinnah-portrait-at-amu-is-false.": 1,
    "Citation support is uncertain for https://www.altnews.in/aaj-tak-falselt-claims-congress-candidate-maskoor-usmani-hung-jinnahs-portrait-at-amu/.": 1,
    "Citation support is uncertain for https://timesofindia.indiatimes.com/city/agra/explain-compulsion-of-putting-jinnahs-picture-in-amu-bjp-mp-to-amu-vc/articleshow/63976930.cms.": 1,
    "Citation support is uncertain for http://joannematteraartblog.blogspot.com/2020/10/the-journal-of-scroll-down-for-newest.html.": 1,
    "A personal blog (Joanne Mattera Art Blog) asserts the quote is true, contradicting the findings of AP, Snopes, and Daily Caller.": 1,
    "Resolve and cite the assertion: A man who received four ballot applications votes four times in the 2020 election.": 1,
    "Citation support is uncertain for https://publicworks.jacksonms.gov/scholarship/SuLmnT/3OK060/did__kamala-harris_fail_the__bar-exam.pdf.": 1,
    "Two PDF documents from non-news domains contradict the reporting of the New York Times and subsequent fact-checks, claiming she passed on her first attempt.": 1,
    "Resolve and cite the assertion: Controversial abortion methods are allowed under New Zealand's Abortion Legislation Act (2020).": 1,
    "Definition of 'controversial abortion methods' in the context of the claim.": 1,
    "Specific list of permitted or prohibited medical methods of abortion under the 2020 Act.": 1,
    "Clinical guidelines or regulations that supplement the Act regarding the actual procedures used (the provided snippet for the Clinical Guideline does not list specific methods).": 1,
    "Citation support is uncertain for https://www.theguardian.com/us-news/2020/sep/03/ed-markey-primary-victory-climate-crisis.": 1,
    "Biden's verbal statement 'I don't support the Green New Deal' directly contradicts his campaign website's description of the GND as a 'crucial framework'.": 1,
    "Citation support is uncertain for https://www.npr.org/2021/04/02/983398361/green-new-deal-leaders-see-biden-climate-plans-as-a-victory-kind-of.": 1,
    "Citation support is uncertain for https://www.thehindu.com/news/national/other-states/tanishq-store-in-gujarat-puts-up-apology-note-over-withdrawn-ad/article61718348.ece.": 1,
    "Citation support is uncertain for https://en.wikipedia.org/wiki/List_of_federal_judges_appointed_by_Donald_Trump.": 2,
    "The claim identifies Trump as 'Former President' on Oct 13, 2020, while historical records show he was the incumbent President.": 1,
    "Citation support is uncertain for https://ballotpedia.org/Supreme_Court_vacancy,_2020.": 1,
    "Citation unrelated the finding: https://ballotpedia.org/Supreme_Court_vacancy,_2020.": 1,
    "The records do not provide a single primary source that uses the exact phrase 'lost the popular vote by 3 million', though they provide the precise figure of 2.87 million.": 1,
    "Resolve and cite the assertion: Amy Coney Barrett, associate justice of the Supreme Court of the United States,  said during her Supreme Court confirmation hearing that she was not using notes because she has seven kids and is used to stupid questions.": 1,
    "Citation support is uncertain for https://www.wral.com/archive/19338911/.": 1,
    "Citation support is uncertain for https://www.reuters.com/article/fact-check/cnn-did-not-report-trump-died-on-nov-1-2022-idUSL1N31Y1Y3/.": 1,
    "Citation support is uncertain for https://politifact.com/article/2020/oct/08/kamala-harris-jumped-conclusions-about-abraham-lin/.": 1,
    "Citation support is uncertain for https://www.premiumtimesng.com/news/more-news/420226-endsars-kiki-osinbajo-declares-support-zahra-buhari-too-but-later-deleted-post.html.": 1,
    "Citation support is uncertain for https://dubawa.org/misleading-newspaper-report-claims-daughters-of-buhari-osinbajo-facilitated-dissolution-of-sars/.": 1,
    "Citation support is uncertain for https://x.com/dintentdata/status/1771552678704779719?ref_src=twsrc%5Etfw.": 1,
    "Citation support is uncertain for https://www.snopes.com/news/2016/06/23/donald-trump-rape-lawsuit/.": 1,
    "Observational studies in Norway and Vermont report higher infection rates for mask wearers, while the CDC California study and various meta-analyses report lower infection rates for mask wearers.": 1,
    "Lack of a single, definitive, large-scale RCT that resolves the conflict between observational studies showing increased risk (due to behavior) and those showing decreased risk.": 1,
    "The literal text of the quote is accurate, but the omission of the subsequent clause ('...when I had run as a proud Democrat for vice president, and I\u2019m running as a proud Democrat for president') fundamentally changes the meaning of the statement.": 1,
    "Citation support is uncertain for https://dcgary.org/news/artemis-ii-mission-prompts-look-catholics-longtime-interest-space-exploration.": 1,
    "Citation support is uncertain for https://www.nbcnews.com/id/wbna43120039.": 1,
    "A reconciled explanation for the discrepancy between the World Bank's 1.8% growth figure and the NBS's -1.92% figure for 2020.": 1,
    "NBS (via Trading Economics) reports a full-year 2020 GDP contraction of -1.92%, while the World Bank Climate Portal reports a growth of 1.8%.": 1,
    "Julia Grant's 1899 statement that 'we owned slaves ourselves when the war began' contradicts the legal record and the findings of historians who state Grant had no legal ownership after 1859.": 1,
    "Resolve and cite the assertion: Dr. Anthony Fauci said of Trump\u2019s pandemic response, \u201cI can\u2019t imagine that \u2026 anybody could be doing more.\u201d": 1,
    "The Trump campaign asserts the quote praised the administration/President, whereas Dr. Fauci asserts it praised the federal public health officials/task force.": 1,
    "Resolve and cite the assertion: tradition. We cannot stop it!\u201d": 1,
    "Citation support is uncertain for https://fullfact.org/health/covid-deaths/.": 1,
    "Lack of independent verification of the coach's recordings mentioned by some news sources to confirm if the coach's statements were accurately reported or if he was speaking on behalf of the parents.": 1,
    "Coach Pascal Bruhin claims the parents refused due to safety reports; parents Igor and Valerie Allinckx claim the coach's statement is a 'lie' and the decision was based on holidays and fatigue.": 1,
    "The claim attributes the reversal entirely to Labor, whereas the evidence shows the LNP restored most of the positions themselves before the change of government.": 1,
    "Lack of post-implementation data on the number of individuals denied coverage under the SF 2349 plans.": 1,
    "Absence of an official audit or report quantifying the net change in health care access specifically attributed to the bill's enactment.": 1,
    "Resolve and cite the assertion: No one lost their health care because of the Wellmark": 1,
    "Citation support is uncertain for https://www.desmoinesregister.com/story/news/health/2018/04/02/non-obamcare-plans-wellmark-and-farm-bureau-approved-iowa-governor-reynolds/478100002/.": 1,
    "Resolve and cite the assertion: No one lost their health care because of the Wellmark and Iowa Farm Bureau Health Plan Bill.": 1,
    "Total energy consumption renewables (~28%) vs. Electricity generation renewables (~62-67%).": 1,
    "No source provides a '40%' figure for any current renewable energy metric in Iowa.": 1,
    "Early 2020 reports (NPR, AEI/Royal College of Paediatrics) state the role of children in transmission is 'unknown', whereas 2021 peer-reviewed studies (NEJM/PMC) provide evidence of child-to-adult transmission.": 1,
    "Citation support is uncertain for https://pmc.ncbi.nlm.nih.gov/articles/PMC8382134/.": 1,
    "Resolve and cite the assertion: A campaign ad video for John Cornyn says that his plan would guarantee insurers must sell plans to any patient with preexisting conditions": 1,
    "Lack of a full, verified transcript of all versions of the 'Will Be Covered' ad to see if the 'guarantee insurers must sell plans' language exists in a different cut.": 1,
    "Citation support is uncertain for https://en.wikipedia.org/wiki/Charlotta_Bass.": 1,
    "Citation support is uncertain for https://www.cdc.gov/nchs/nvss/vsrr/covid19/excess_deaths.htm.": 1,
    "The exact origin of the 4.4% figure used by Winston Peters remains unidentified in the provided records.": 1,
    "Winston Peters claims 4.4% of GDP, whereas Treasury and the Commission for Financial Capability report 4.8% of GDP.": 1,
    "Citation support is uncertain for https://www.theguardian.com/world/2021/feb/15/nigerias-ngozi-okonjo-iweala-confirmed-as-wto-chief.": 1,
    "Citation support is uncertain for https://factcheck.afp.com/nigerias-okonjo-iweala-has-not-been-named-head-world-trade-organization-she-final-contender.": 1,
    "Citation support is uncertain for https://www.nytimes.com/2021/02/15/business/economy/wto-okonjo-iweala-director-general.html.": 1,
    "Mike Pence frames the one-month gap as 'hesitation' that cost a life; ABC News reporting frames it as a period used to 'confirm and bolster' intelligence before a high-risk operation.": 1,
    "Lack of primary military or intelligence records to confirm the exact date the rescue plan was presented versus the date of authorization.": 1,
    "No record explicitly mentions the figure '11.6 million jobs' added back.": 1,
    "Resolve and cite the assertion: Right after a time where we're going through a pandemic that lost 22 million jobs at the height, we've already added back 11.6 million jobs.": 1,
    "The exact breakdown of the 300,000 jobs by sector from the original Moody's report is not provided in the retrieved texts.": 1,
    "The claim specifies 'manufacturing jobs,' but the source text specifies 'U.S. employment' generally.": 1,
    "Direct contradiction between the stated goals of candidates like Sanders/Warren (total ban) and Biden (no total ban).": 1,
    "Citation support is uncertain for https://factcheck.afp.com/it-not-joe-bidens-policy-ban-fracking.": 1,
    "The identity of the 'I' in the specific claim phrasing 'President Trump and I' is not explicitly identified in the provided records, though the context suggests a political partner (e.g., Mike Pence).": 1,
    "The administration claims to 'guarantee' protection for pre-existing conditions while simultaneously backing a lawsuit to invalidate the law (ACA) that provides those legal guarantees.": 1,
    "The retrieved records are primarily fact-checks; direct access to the original 2015 patent text was not provided, though it was summarized by the European Patent Office spokesperson.": 1,
    "News reports state the treatment was 'developed using cells derived from human fetal tissue,' while Regeneron and USA Today state it was 'not made from' fetal tissue, distinguishing between the testing process and the production of the drug.": 1,
    "The full peer-reviewed text of the June 2020 'Science' paper was not provided, only references to its supplementary materials via news reports and a separate unrelated paper.": 1,
    "Citation support is uncertain for https://www.cbsnews.com/news/regeneron-trump-covid-aborted-fetal-tissue/.": 1,
    "The literal phrasing 'this is their new hoax' following a discussion of coronavirus is contrasted with the President's explicit clarification that he was referring to the 'politicizing' of the virus.": 1,
    "Citation support is uncertain for https://www.snopes.com/fact-check/trump-coronavirus-rally-remark/.": 1,
    "Citation support is uncertain for https://www.judiciary.senate.gov/press/rep/releases/chairman-graham-releases-information-from-dni-ratcliffe-on-fbis-handling-of-crossfire-hurricane.": 1,
    "Mike Pence claims Democrats tried to 'overturn' the 2016 election, whereas other sources argue that Democratic actions (like Hillary Clinton's comments) did not constitute an attempt to overturn the results.": 1,
    "The Russian Foreign Ministry claims the OPCW findings are a 'fantastic story' and 'conspiracy', whereas the OPCW and laboratories in Germany, France, and Sweden claim the findings are based on independent biomedical analysis of samples.": 1,
    "Citation support is uncertain for https://politifact.com/factchecks/2017/dec/18/usa-front/fake-news-says-chuck-schumer-had-affair-teenage-ch/.": 1,
    "Lack of a single, current, universally accepted 'extreme poverty' percentage for the total Nigerian population across all cited sources.": 1,
    "World Bank 2025 estimates 50.8% extreme poverty, while UNCTAD 2022 estimates 41.8%, and NBS 2018/19 estimates 40.1% (national) or 30.9% (international).": 1,
    "Inconsistency in the definition of 'extreme poverty' (e.g., $2.15/day vs $3/day vs national poverty line).": 1,
    "Citation support is uncertain for https://nigerianstat.gov.ng/elibrary/read/1092.": 1,
    "Citation support is uncertain for https://www.fox29.com/news/gop-lawmaker-introduces-resolution-to-expel-nancy-pelosi-from-house.": 1,
    "Citation support is uncertain for https://www.texastribune.org/2020/10/05/donald-trump-coronavirus-hospital/.": 1,
    "Lack of large-scale, gold-standard arterial blood gas studies specifically correlating behind-mask CO2 levels with systemic intoxication across diverse populations.": 1,
    "Akhondi et al. conclude that masks increase CO2 to levels associated with toxicity based on breathing-zone measurements, whereas Grimm et al. and Catanzaro et al. find that systemic blood gas changes do not lead to clinical intoxication.": 1,
    "Citation support is uncertain for https://www.nature.com/articles/s41598-022-13711-2.": 1,
    "Citation support is uncertain for https://www.frontiersin.org/journals/pediatrics/articles/10.3389/fped.2026.1679586/full.": 1,
    "The primary source for the \u00a390bn figure (Richard Murphy) attributes only \u00a311bn to avoidance, while the claim attributes the full \u00a390bn to avoidance.": 1,
    "HMRC official figures (\u00a332bn-\u00a334bn) contradict the independent estimate of the total gap (\u00a390bn).": 1,
    "Dr. Conley's October 3 statement that the president was not on oxygen vs. his October 4 admission that the president received oxygen on Friday morning.": 1,
    "Lack of peer-reviewed medical records or official hospital charts to verify the exact duration and necessity of oxygen use beyond the physician's public statements.": 1,
    "Resolve and cite the assertion: President Trump is not on supplemental oxygen.": 1,
    "Confirmation of whether 'Amuzu Hospital' and 'Amuzu Health Centre' are the same entity and if they employ a 'Dr. Ebeneezer'.": 1,
    "Resolve and cite the assertion: Dr. Ebeneezer, a medical doctor": 1,
    "Verification of Dr. Ebeneezer's actual medical license via the Medical and Dental Council of Nigeria (MDCN).": 1,
    "The claim uses the word 'avoid' (implying prevention), whereas the cited scientific evidence only supports 'lower risk' (hazard ratio < 1.0).": 1,
    "Resolve and cite the assertion: The ex-Prime Minister of India Lal Bahadur Shastri took a loan to buy a car.": 1,
    "Citation support is uncertain for https://www.cbc.ca/news/world/child-organ-trafficking-ring-busted-by-mexican-police-1.2576492.": 1,
    "Lack of official government or pension records showing the deduction for loan repayment.": 1,
    "Absence of independent corroboration beyond the family's oral testimony and subsequent media repetition.": 1,
    "Resolve and cite the assertion: The wife of  Lal Bahadur Shastri (ex Prime minister of India) repaid his car loan after his death.": 1,
    "Lack of primary bank records from Punjab National Bank to verify the loan account and repayment transactions.": 1,
    "The loan amount is cited as Rs 5,000 in all news reports, but as Rs 75,000 in one Instagram post.": 1,
    "Citation support is uncertain for https://www.usatoday.com/story/news/factcheck/2020/10/03/fact-check-false-claim-trumps-covid-19-test-result-con/5894945002/.": 2,
    "Citation support is uncertain for https://www.factcheck.org/2020/10/misinformation-speculation-follow-trump-covid-19-diagnosis/.": 1,
    "Citation support is uncertain for https://politifact.com/article/2020/oct/02/evidence-trump-telling-truth-about-his-positive-co/.": 1,
    "Citation support is uncertain for https://www.mprnews.org/story/2020/10/02/misinformation-spikes-as-trump-confirms-covid19-diagnosis.": 1,
    "No transcript or report of a speech given by Joe Biden on October 2, 2020, containing job creation figures was retrieved.": 1,
    "Resolve and cite the assertion: During a speech on 2nd October 2020 Joe Biden said he would create 550 million new jobs.": 1,
    "Citation support is uncertain for https://dailycaller.com/author/elias-atienza/page/49/.": 1,
    "The full text of the Daily Caller fact check regarding the '550 million jobs' claim is missing.": 1,
    "Citation support is uncertain for https://www.bbc.com/news/blogs-trending-54387438.": 1,
    "Citation support is uncertain for https://www.poynter.org/fact-checking/2020/fact-checking-misinformation-about-president-trumps-covid-19-diagnosis/.": 1,
    "Citation support is uncertain for https://www.who.int/news-room/spotlight/influenza-are-we-ready/5-myths-about-the-flu-vaccine.": 1,
    "Lack of independent, peer-reviewed economic analysis specifically comparing the 2020 cost structures (refining, transport, subsidies) of Nigeria and Saudi Arabia to determine if the price difference was 'sensible' from a fiscal perspective.": 1,
    "President Buhari views the price comparison as a logical basis for adjustment, whereas Wale Alonge views the comparison as fundamentally flawed ('Jupiter with Mars') due to population-to-resource ratios.": 1,
    "Citation support is uncertain for https://www.military.com/daily-news/2020/10/02/launch-of-e-6-nuclear-command-plane-not-tied-trumps-covid-19-diagnosis-pentagon.html.": 1,
    "A single World Bank PDF snippet claims a population of 'about 36 million', which contradicts the UN and Macrotrends data.": 1,
    "The Hathras District Magistrate's claim of family consent directly contradicts the statements of the victim's father, brother, and mother.": 1,
    "The IPS Journal claims 'Bilateral trade continued to decline' during the Trump period, whereas US Census Bureau data shows total trade volume rose from $55.47B in 2017 to $56.90B in 2019.": 1,
    "Lack of a single source that explains why qualitative reports (IPS Journal, MG) claim trade 'continued to decline' while Census data shows a volume increase from 2017 to 2019.": 1,
    "A Medium article contradicts the 200 million figure, claiming the population is closer to 100 million, but this is an outlier compared to institutional data.": 1,
    "Resolve and cite the assertion: Other Countries Have Proved that the U.S. FDA Was Wrong to Withdraw Approval Of Hydroxychloroquine as COVID Drug": 1,
    "No peer-reviewed medical journal case reports were provided in the retrieved records, only news reports and official government archives.": 1,
    "Citation support is uncertain for https://www.cnbc.com/2020/10/02/president-donald-trump-says-he-has-tested-positive-for-coronavirus.html.": 1,
    "Citation support is uncertain for https://africacheck.org/fact-checks/reports/nigerias-population-economy-and-history-fact-checking-buharis-independence-day.": 2,
    "Clarification on whether the '60%' refers to total revenue, oil revenue, or a specific quarterly drop.": 1,
    "The Vice President and Finance Minister claim a massive revenue drop (60-65%), while Femi Falana claims oil income in the first half of 2020 was 13% higher than the previous year.": 1,
    "Lack of primary budgetary data (actual Naira figures for 2020) to calculate the exact percentage drop relative to 2019.": 1,
    "World Bank data (42.8m) contradicts the 45 million figure cited by other sources.": 1,
    "Lack of access to the original 1960 census document or official British colonial gazette to confirm the primary source of the 45 million figure.": 1,
    "President Buhari claims the price comparison is a logical basis for pricing; Dr. Adewale Alonge claims the comparison is logically invalid due to population and reserve per capita differences.": 1,
    "Lack of independent, third-party verification of the specific N161 vs N168 pump prices cited by Buhari in October 2020.": 1,
    "The YouTube snippet does not provide the date or the specific government report it references.": 1,
    "One source claims a 60% drop in revenue (YouTube), while another claims monthly revenue rose from \u20a6711 billion to \u20a63.6 trillion (Facebook/Rant HQ).": 1,
    "Lack of primary official NBS/CBN documents to verify the '60% drop' mentioned in the YouTube snippet.": 1,
    "No record confirms a specific 40% price drop for oil; the 40% figure in the records refers to total exports.": 1,
    "One source reports a slump of 'over 50%' for the benchmark price, while the claim specifies 40%.": 1,
    "Resolve and cite the assertion: There was a 40% drop in oil prices in Nigeria.": 1,
    "The World Bank snippet lists 42.8m for 1960, which is slightly lower than 45m, though still within a reasonable range of 'about 45 million'.": 1,
    "The sources provisioservices.com and provisiodigital.com appear to be the same entity or sharing the same data, reducing source independence.": 1,
    "Citation support is uncertain for https://provisioservices.com/nigeria-at-60/.": 1,
    "Lack of a single authoritative government record providing the exact day-count of military vs civilian rule.": 1,
    "Macrothink claims 29 years; Provisio Services claims 28 years and 11 months; ReportHype claims 33 years.": 1,
    "Citation support is uncertain for https://2009-2017.state.gov/outofdate/bgn/nigeria/10801.htm.": 1,
    "Citation support is uncertain for https://www.facebook.com/NNNGO/posts/according-to-latest-united-nations-data-as-of-monday-october-31-2022-the-current/10160292638786460/.": 1,
    "Wikipedia states 54.3% while other sources state 52%.": 1,
    "Lack of a direct, original UN DESA PDF or database export to confirm the exact 52% figure without relying on third-party aggregators like IndexMundi or Worldometer.": 1,
    "Absence of a recent, undisputed national census to provide a baseline.": 1,
    "Citation support is uncertain for https://worldpopulationreview.com/countries/nigeria.": 1,
    "Lack of a single, peer-reviewed, country-wide satellite-based population audit to resolve the discrepancy between UN estimates and critical estimates.": 1,
    "UN/Worldometer estimates (~243M) vs. critical/satellite-based estimates (160M-180M).": 1,
    "Official projections based on 2006 data vs. current NIN registration trends and critical demographic analysis.": 1,
    "UN-Habitat (52% in 2020) vs. The Global Economy/UN Population Division (59.77% in 2020) vs. Wikipedia (54.3%).": 1,
    "Discrepancy between UN-Habitat's 52% (2020) and The Global Economy's 59.77% (2020), both attributing to UN-related data.": 1,
    "Lack of a completed, verified national census since 2006 to resolve the discrepancy between UN projections and critical estimates.": 1,
    "Citation support is uncertain for https://eie.ng/press-statement-postponed-2023-population-and-housing-census/.": 1,
    "UN-based estimates (240m+) vs. critical analysis suggesting inflation (160-180m).": 1,
    "Temporal inconsistency: data ranges from September 2024 to October 2026.": 1,
    "Aliko Dangote claims Nigeria is 40% cheaper, while other reports (e.g., Saudi Life Guide) show Nigeria is significantly more expensive ($0.985 vs $0.622).": 1,
    "StatiSense claims Nigeria ($0.589) is cheaper than Saudi Arabia ($0.621), while beats-onit.com claims Saudi Arabia (62 cents) is cheaper than Nigeria (67 cents).": 1,
    "Lack of a synchronized, real-time global price index to resolve the conflict between sources.": 1,
    "World Bank data (42.8m) contradicts UN World Population Prospects data (45.05m/45.1m) for the year 1960.": 1,
    "Lack of access to the original 1960 colonial census or official government gazette from the period of independence to resolve the UN/World Bank discrepancy.": 1,
    "The claim specifies 40%, but evidence points to 47% (budget benchmark) or >50% (market price).": 1,
    "Lack of a completed official national census after 2011 to provide a definitive current percentage.": 1,
    "Official census data (54.7% majority) contradicts amateur projections and social media claims (suggesting they are a minority or becoming one).": 1,
    "Citation support is uncertain for https://www.reddit.com/r/HindutvaRises/comments/1eknbtg/the_truth_about_hindu_majority_of_kerala/.": 1,
    "Citation support is uncertain for https://rameshsukumaran.medium.com/keralas-religious-demography-a-study-1203a06a92b2.": 1,
    "Citation contradicts the finding: https://documents1.worldbank.org/curated/en/841301468333908334/pdf/multi0page.pdf.": 1,
    "Clarification on why the World Bank's internal document (36m) differs from its Open Data portal (42.8m) and the UN estimates (45m).": 1,
    "Citation support is uncertain for https://futures.issafrica.org/geographic/guide.pdf?geography=NG&topic=02-current-path.": 1,
    "Citation support is uncertain for https://nationalpopulation.gov.ng/census-enumeration.": 1,
    "World Bank document (36 million) vs. World Bank Open Data (42.8 million) vs. UN/Secondary sources (45 million).": 1,
    "Direct access to the original colonial-era demographic records used to generate these estimates is still missing.": 1,
    "Direct confirmation of a 40% decrease in the unit price (per barrel) of Brent or Bonny Light oil over a specific timeframe.": 1,
    "Clarification on whether the claim is conflating 'export value' with 'unit price'.": 1,
    "Resolve and cite the assertion: There was a 40% drop in the price of oil, Nigeria's main export.": 1,
    "The Reuters snippet attributes the 40.3% figure to 'exports' rather than 'price'.": 1,
    "The claim suggests a \u00a33,000 fine is the standard or likely penalty, whereas primary reporting and fact-checks indicate the standard fine was \u00a3100-\u00a3200, with \u00a33,000+ being reserved for repeat offenders.": 1,
    "Citation support is uncertain for https://www.smithsonianmag.com/science-nature/what-have-we-learned-from-intentionally-infecting-people-with-covid-19-180985794/.": 1,
    "Citation support is uncertain for https://pmc.ncbi.nlm.nih.gov/articles/PMC9351604/.": 1,
    "Direct response from PAHO regarding the 'pertinence' of the U.S. concerns beyond the audit reports.": 1,
    "Cuba claims the matter is not pertinent to PAHO; evidence shows PAHO was the financial intermediary and conducted audits on the program.": 1,
    "Cuba claims the concerns are not legitimate; U.S. and HRW claim they are based on human trafficking.": 1,
    "Absolute officer numbers rose (refuting the claim), but the officer-to-population ratio fell (supporting the claim).": 1,
    "Citation support is uncertain for https://www.reuters.com/article/world/fact-check-biden-was-not-given-presidential-debate-questions-in-advance-by-mode-idUSKBN26M6N7/.": 1,
    "Citation support is uncertain for https://www.factcheck.org/2020/09/baseless-online-claims-target-biden-ahead-of-first-debate/.": 1,
    "Lack of a detailed list of medications in the provided health summary snippet.": 1,
    "Absence of independent medical evaluations or drug test results.": 1,
    "Political figures and one psychiatrist suggest stimulant use, while fact-checking outlets and the Biden campaign state there is no evidence.": 1,
    "Resolve and cite the assertion: Potential voter fraud in the 2020 U.S Presidential Election is caused by mail-in ballots being sent to a mans  deceased parents in Mercer County in New Jersey.": 1,
    "No specific record of a man in Mercer County receiving ballots for deceased parents.": 1,
    "Citation support is uncertain for https://pmc.ncbi.nlm.nih.gov/articles/PMC4237196/.": 1,
    "Joe Biden's characterization of the record as 'adamant' vs. Politifact's characterization of the record as 'more academic than \"adamant\"' and 'not very lengthy'.": 1,
    "The full text of the 2015 'On Point' radio interview is not available to verify the exact phrasing of her comments on the 'better legal argument'.": 1,
    "Resolve and cite the assertion: A Supreme Court nominee has never been nominated": 1,
    "There is a semantic dispute over the phrase 'already underway.' One source (USA Today) rates the claim as false because 'underway' is interpreted as 'while Americans were voting,' and no historical nominations occurred during the actual voting window. However, other sources (FactCheck.org, PBS) refute the claim by citing nominations and installations that occurred during the election year.": 1,
    "Citation support is uncertain for https://x.com/PIBFactCheck/status/1309371515922649088.": 1,
    "The claim asserts both PMJJBY and PMSBY cover COVID-19, whereas official government (PIB) and independent fact-checkers state only PMJJBY does.": 1,
    "Citation support is uncertain for https://financialservices.gov.in/pmjjby.": 1,
    "Resolve and cite the assertion: Govt of India is providing money to bereaved families of COVID-19 - Insurance benefits for Covid-19 deaths can be claimed under the schemes of PMJJBY and PMSBY.": 1,
    "Citation support is uncertain for https://www.boomlive.in/hoax-forward-about-identifying-fake-500-rupee-notes-resurfaces.": 1,
    "Citation support is uncertain for https://www.thequint.com/news/webqoof/are-500-notes-with-green-strip-close-to-gandhis-image-fake.": 1,
    "The Washington Informer claims Terry Fitzgerald Moorer is the 'only' Black judicial appointment, whereas WUSA9 reports eight Black judges based on FJC data.": 1,
    "Citation support is uncertain for https://news.bloomberglaw.com/us-law-week/no-black-judges-among-trumps-appeals-court-confirmations.": 1,
    "Resolve and cite the assertion: Sunil Gavaskar said that \"Virat Kohli has only trained against Anushka [Sharma]'s balls during the lockdown\"": 1,
    "Citation support is uncertain for https://www.youtube.com/watch?v=BoCJJlsrKQw.": 1,
    "Citation support is uncertain for https://nces.ed.gov/surveys/annualreports/topical-studies/covid/theme/elementary-and-secondary-education-technology-support/.": 1,
    "Citation support is uncertain for https://pmc.ncbi.nlm.nih.gov/articles/PMC7405157/.": 1,
    "Citation support is uncertain for https://la.myneighborhooddata.org/2020/05/computer-internet-access-gaps-for-students-during-covid-19/.": 1,
    "The claim asserts laptops were provided to 'all students', while NCES data explicitly states they were provided to students 'who needed them'.": 1,
    "Citation support is uncertain for https://www.sciencedirect.com/science/article/abs/pii/S1043951X2100047X.": 1,
    "Resolve and cite the assertion: New York City Mayor Bill de Blasio officially ordered all police": 1,
    "Resolve and cite the assertion: citizens to stop sharing the booking photo of his daughter caught up during rioting": 1,
    "Resolve and cite the assertion: New York City Mayor Bill de Blasio officially ordered all police and citizens to stop sharing the booking photo of his daughter caught up during rioting": 1,
    "Lack of any record of a formal mayoral directive, executive order, or official police department memo regarding the sharing of Chiara de Blasio's photos.": 1,
    "Resolve and cite the assertion: Premier Daniel Andrews of the state of Victoria in Australia borrowed money from the IMF and now is in default.": 1,
    "Resolve and cite the assertion: now is in default.": 1,
    "Resolve and cite the assertion: Premier Daniel Andrews of the state of Victoria in Australia borrowed money from the IMF": 1,
    "Resolve and cite the assertion: Americans advised to reconsider travel to Ghana due to COVID-19.": 1,
    "No record explicitly states the travel advisory level for Ghana on 2020-09-22.": 1,
    "The social media snippet mentioning 'Tuesday, September' does not specify the year 2020.": 1,
    "Citation support is uncertain for https://www.abc.net.au/news/2019-10-25/victoria-deepens-links-with-china-controversial-belt-and-road/11636704.": 1,
    "Citation support is uncertain for https://www.premier.vic.gov.au/victoria-and-china-take-partnership-next-level.": 1,
    "Citation support is uncertain for https://www.reddit.com/r/AustralianPolitics/comments/1vfn4wp/labors_water_bombshell_secret_privatisation_plan/.": 1,
    "Lack of formal economic modeling specifically linking the 100% renewable target to consumer retail price increases.": 1,
    "The IEA mentions 'considerable costs' of the 100% target, whereas Te Waihanga reports that the cost of building renewable generation (wind/solar) has halved or fallen by two-thirds.": 1,
    "Absence of data on whether the 'considerable costs' of the final transition phase are funded via government subsidies or passed to consumers.": 1,
    "Lack of a formal, peer-reviewed clinical cognitive assessment report (neurocognitive testing) for Joe Biden.": 1,
    "The Special Counsel's report describes 'diminished faculties,' whereas the president's physician and a geriatrician describe 'benign age-associated memory impairment' and 'no signs of Alzheimer's.'": 1,
    "Critics (e.g., Heritage Foundation, Jack Brewer) claim the 'disrupt' language is a call for 'destruction' of the family, while academics (e.g., Davin L. Phoenix) claim it is a call to 'disrupt the notion that the nuclear family structure is the only way to ensure neighborhood stability'.": 1,
    "Citation support is uncertain for https://www.independentwomen.com/2020/10/01/fact-check-is-it-true-that-black-lives-matter-wants-to-abolish-the-nuclear-family/.": 1,
    "Lack of an official statement from Black Lives Matter explaining why the 'What We Believe' page was removed or clarifying the intent of the 'disrupt' language.": 1,
    "Citation support is uncertain for https://sports.yahoo.com/articles/michael-jordan-explains-why-decided-145811281.html.": 1,
    "The 1977 report's text literally mentions 'less than 12 years old' in a recommendation, but secondary analysis (Volokh, FactCheck.org) proves this was a clerical error citing the wrong section of S. 1400.": 1,
    "The September 14-28 poll (1% voted) and the October 16-27 poll (36% voted) create a wide gap, making it impossible to pinpoint the status on October 1 without more granular data.": 1,
    "Specific voting percentages for the date of October 1, 2020.": 1,
    "Resolve and cite the assertion: 30% to 40% of Americans will have voted by Oct. 1. 2020": 1,
    "Citation unrelated the finding: https://www.oyez.org/justices/ruth_bader_ginsburg.": 1,
    "Citation support is uncertain for https://www.facebook.com/christinaloreynews/posts/age-is-just-a-number-the-notorious-rbg-ruth-bader-ginsburg-was-known-for-her-rel/1532149055399001/.": 1,
    "Citation support is uncertain for https://politifact.com/factchecks/2020/sep/22/joe-biden/bidens-false-claim-about-when-trump-campaign-calle/.": 2,
    "Citation support is uncertain for https://www.factcheck.org/2020/09/bidens-false-and-exaggerated-supreme-court-claims/.": 1,
    "Resolve and cite the assertion: Trump campaign asked Joe Biden to release a list of potential Supreme Court picks only after Ginsburg\u2019s passing": 1,
    "House authorities state MPs are exempt from mask mandates, while unions and health experts state MPs are ignoring general government guidance for crowded spaces.": 1,
    "Citation support is uncertain for https://www.bbc.com/news/uk-politics-59056316.": 1,
    "Resolve and cite the assertion: MPs are not following workplace Covid guidance by wearing masks.": 1,
    "Lack of a named individual associated with the alleged incident.": 1,
    "Absence of official police, coroner, or reputable news reports confirming a death on September 19, 2020, in London.": 1,
    "Resolve and cite the assertion: A man died in police custody after a 19th September 2020 anti-lockdown protest in London.": 1,
    "No specific case in the IOPC 2020/21 report matches the date and context of the claim.": 1,
    "Wikipedia and The List state the marriage occurred in 1997, whereas IMDb and Fandom state the date was May 29, 1999.": 1,
    "The exact date of the marriage remains inconsistent across sources (1997 vs 1999).": 1,
    "Mitch McConnell's 2016 statement that the people should 'have a voice' in an election year contradicts his 2020 action of confirming a justice weeks before the election.": 1,
    "Lack of direct, comprehensive rebuttals from all 31 mentioned Republican senators to address the specific contradiction of their 2016 statements.": 1,
    "Citation contradicts the finding: https://www.jogh.org/documents/issue202002/jogh-10-020388.htm.": 1,
    "Lack of primary Soviet archival documentation to definitively confirm if an open-casket viewing occurred for the public or officials.": 1,
    "Absence of a definitive, authenticated source for the photograph's origin (e.g., official agency metadata) to distinguish between an autopsy photo and a funeral photo.": 1,
    "Citation support is uncertain for https://newsmeter.in/fact-check-picture-showing-charred-body-in-an-open-coffin-is-indeed-of-vladimir-komarov.": 1,
    "Sources claim the photo is from an 'open-casket funeral' vs. sources claiming it is from an 'autopsy' and the funeral used an urn of ashes.": 1,
    "Citation support is uncertain for https://www.factcheck.org/2020/09/ginsburg-was-confirmed-years-before-the-1996-election/.": 1,
    "Citation support is uncertain for https://politifact.com/factchecks/2020/sep/22/facebook-posts/no-ruth-bader-ginsburg-wasnt-confirmed-supreme-cou/.": 1,
    "Resolve and cite the assertion: Ruth Bader Ginsburg was nominated": 1,
    "Startup Intros lists him as CEO of Sightway Capital, while MarketScreener and others list him as CIO.": 1,
    "Lack of a definitive corporate charter for Sightway Capital specifying if 'Managing Director' was a title held within that specific entity or only at the parent Two Sigma Investments.": 1,
    "Citation support is uncertain for https://www.reuters.com/article/world/fact-checkruth-bader-ginsburgquote-on-pedophiliais-made-up-idUSKBN26J29A/.": 1,
    "Citation support is uncertain for https://apnews.com/article/archive-fact-checking-9411725883.": 1,
    "Citation support is uncertain for https://www.aap.com.au/factcheck/a-black-woman-did-not-write-shakespeares-plays/.": 1,
    "Lack of primary Canadian government statements from September 2020 specifically expressing a desire to reopen (most records from that period show extensions of closures).": 1,
    "Donald Trump's claim that Canada wanted the border open contradicts Prime Minister Trudeau's March 2021 statement that it was 'not for today' and reports that the government viewed reopening talks as 'premature'.": 1,
    "Citation support is uncertain for https://pmc.ncbi.nlm.nih.gov/articles/PMC7993552/.": 1,
    "Resolve and cite the assertion: offers help to Putin for Siberian wildfires.": 1,
    "The claim suggests a universal financial impact on 100 million people, but evidence shows that those with employer-sponsored insurance would not necessarily face higher premiums.": 1,
    "The DCCC/Mucarsel-Powell campaign claims the car remained taxpayer-funded during his time in office, whereas the County Budget Director states he assumed the lease personally upon becoming mayor.": 1,
    "Citation support is uncertain for https://www.cidrap.umn.edu/covid-19/scientists-exactly-zero-evidence-covid-19-came-lab.": 1,
    "The claim frames the event as a 'pay raise' (implying a net increase in compensation over time), whereas the evidence shows it was a 'restoration' of a salary he had previously cut.": 1,
    "Citation support is uncertain for https://politifact.com/factchecks/2020/sep/23/joe-biden/fact-checking-bidens-claim-about-number-students-w/.": 1,
    "MPR News states it is 'incorrect to say the police department has been defunded' when referring to overhaul/abolition, while simultaneously confirming the Council 'moved $1.1 million from the police to the health department'.": 1,
    "The exact total police budget for the 2020-2021 period is cited as $179 million in one source, but a precise consolidated figure for the entire fiscal year to calculate the exact percentage of the $8M-$19M cut is not explicitly provided in a single table.": 1,
    "Citation support is uncertain for https://www.nbcbayarea.com/news/california/fewer-in-person-polling-places-in-california-on-election-day/2387060/.": 1,
    "Citation support is uncertain for https://www.boomlive.in/fake-news/forced-to-vote-for-the-shiv-sena-kangana-ranauts-claim-is-false-9805.": 1,
    "Citation support is uncertain for https://pmc.ncbi.nlm.nih.gov/articles/PMC11401773/.": 1,
    "Citation support is uncertain for https://www.news18.com/movies/bollywood/mukesh-khanna-calls-out-jaya-bachchans-behaviour-amid-parliament-video-row-journalists-ke-sath-ws-l-9508725.html.": 1,
    "Citation support is uncertain for https://countercurrents.org/2020/10/more-than-a-hundred-veterans-counter-the-social-media-propaganda-that-muslim-regiment-refused-to-fight-against-pakistan/.": 1,
    "No specific record of 'Millions In TV Ads' allegation was found to be explicitly refuted by a detailed expenditure report, though general non-donation claims were verified.": 1,
    "The claim asserts AARP is 'Prohibited From Involvement In Any Political Campaigns,' but AARP's own IRS definition page states a 501(c)(4) 'may engage in some political activities.'": 1,
    "Citation support is uncertain for https://www.pbs.org/newshour/nation/what-is-antifa-a-look-at-the-movement-trump-is-blaming-for-violence-at-protests.": 1,
    "There is a contradiction regarding the 'average' stringency of the lockdown compared to Australia: the Oxford Covid Stringency Index suggests NZ was slightly more liberal on average (58.5 vs 64), but economists argue the initial 'Level 4' intensity caused a 'colder start' that outweighed the average.": 1,
    "Resolve and cite the assertion: Wildfires do not Affect Mexico And Canada": 1,
    "Citation support is uncertain for https://www.cnn.com/2025/07/09/politics/comey-brennan-ratcliffe-fbi-cia-referral.": 1,
    "CDC data shows precipitous drops under Democrats, while Guttmacher data shows a consistent decline across both parties.": 1,
    "Direct side-by-side comparison tables of Guttmacher vs. CDC rates specifically mapped to presidential term years are not provided in the text, only summaries of the trends.": 1,
    "Supporters attribute the decline to Democratic policies on contraception; critics attribute it to pro-life state-level legislation.": 1,
    "Citation support is uncertain for https://www.channelstv.com/2025/11/06/senate-orders-nafdac-to-enforce-sachet-alcohol-ban-from-december-2025/.": 1,
    "There was a period of significant contradiction between NAFDAC (enforcing the ban) and the OSGF (ordering a suspension of enforcement), but this was a conflict over implementation/timing rather than the existence of the ban itself.": 1,
    "Citation support is uncertain for https://movendi.ngo/policy-updates/2026/08/30/nigeria-launches-new-national-alcohol-policy/.": 1,
    "Citation support is uncertain for https://www.factcheck.org/2020/09/trump-spins-quotes-by-about-biden/.": 1,
    "The literal text of the quote supports the claim, but the speaker's stated intent (vaccine rollout vs. overall management) contradicts the claim's implication.": 1,
    "Citation support is uncertain for https://www.usatoday.com/story/news/factcheck/2020/09/17/fact-check-false-claim-netflix-ceo-reed-hastings-arrested/5801033002/.": 1,
    "Citation support is uncertain for https://www.reuters.com/world/us/police-debunk-social-media-misinformation-linking-oregon-wildfires-activists-2020-09-11/.": 1,
    "Citation support is uncertain for https://www.theguardian.com/us-news/2020/sep/19/police-antifa-arson-wildfire-conspiracy-theories.": 1,
    "Opponents claim the quote is a general statement about law enforcement; the Biden campaign and fact-checkers claim it is a specific statement about the use of military equipment.": 1,
    "Citation support is uncertain for https://www.thehindu.com/news/national/upsc-cse-2026-news-rules-for-serving-civil-servants-what-changed/article70595368.ece.": 1,
    "Lack of independent verification of the 'YugaParivartan' data analysis to confirm if the 13-mark difference is a factual average or a skewed sample.": 1,
    "Absence of a direct statement from UPSC regarding whether the '15-point programme' for minorities influences the actual scoring or cut-offs of the Civil Services Exam.": 1,
    "The Swarajya article presents a claim of interview bias (higher marks for Muslims) based on a blogger's analysis, while the same article cites the Sachar Committee Report which found no such bias in earlier years.": 1,
    "Citation support is uncertain for https://factly.in/upsc-civil-services-exam-no-difference-in-attempts-age-criteria-based-on-religion/.": 1,
    "The claim's absolute 'do nothing' vs. peer-reviewed evidence of ~50% filtration efficiency for small aerosols.": 1,
    "The CDC's public-facing guidance ('offer little protection') vs. a spokesperson's clarification ('may help with larger particles and ash').": 1,
    "Citation support is uncertain for https://www.zakatindia.org/Muslim-Presence-in-Bureaucracy.html.": 1,
    "The claim refers to 'aspirants' (applicants), but the primary evidence provided refers to 'recruits' (successful candidates).": 1,
    "Lack of longitudinal data on the total number of Muslim applicants (aspirants) per year.": 1,
    "Lack of official UPSC data on the religious demographics of all exam takers.": 1,
    "Sudarshan News frames the selection of these universities as discriminatory/preferential toward Muslims, whereas JMI and BBAU official texts frame the program as an inclusive effort for all marginalized groups (SC/ST/Minorities/Women).": 1,
    "The provided records are primarily news reports and press releases; while they cite official company statements, they are not peer-reviewed medical journal articles detailing the trial pauses.": 1,
    "Resolve and cite the assertion: Nita Ambani is to give Rs 200 crore for Kangana Ranaut\u2019s new studio": 1,
    "The literal adjusted gross income reported on tax returns contradicts the claim, while the campaign's explanation regarding 'public official salaries' attempts to reconcile the statement.": 1,
    "Citation support is uncertain for https://www.huffingtonpost.co.uk/entry/nhs-test-and-trace-contact-tracing-new-low_uk_5f50d2f4c5b6578026ca1f9a?origin=article-related-life.": 1,
    "The claim asserts that the magazine's actions reveal the hostility of 'political and cultural institutions of the Western world,' but evidence shows Western political figures (e.g., Laurent Fabious, Jay Carney) and cultural figures (e.g., PEN America writers) have criticized the magazine.": 1,
    "Resolve and cite the assertion: The NFL, NBA and MLB have Tax-Exempt status.": 1,
    "Citation support is uncertain for https://www.snopes.com/fact-check/tax-season/.": 1,
    "Citation support is uncertain for https://www.thepolicycircle.org/minibrief/government-community-and-sports-teams-tax-credits/.": 1,
    "Citation support is uncertain for https://www.bbc.com/future/article/20200812-exponential-growth-bias-the-numerical-error-behind-covid-19.": 1,
    "No record identifies a specific 'math mistake' (e.g., a calculation error or flawed formula) that is explicitly linked to the decision to lock down.": 1,
    "Resolve and cite the assertion: Math Mistake Caused U.S. Leaders To Panic": 1,
    "Resolve and cite the assertion: Math Mistake Caused U.S. Leaders To Panic And Order COVID Lockdowns": 1,
    "Resolve and cite the assertion: Video of a man blowing vape smoke through various face masks shows that they do not help prevent the spread of coronavirus.": 1,
    "There is a numerical discrepancy regarding the exact count: ThisDay reports 130 vehicles, while Dubawa references a Channels TV report of 151 vehicles.": 1,
    "No evidence of a connection between Richard Jewell and the fundraising ban mentioned in the claim.": 1,
    "No mention of 'Richard Jewells Defence' in the retrieved records.": 1,
    "Resolve and cite the assertion: Mark Zuckerberg Banned Richard Jewells Defence from raising money on Facebook.": 1,
    "A user comment on Fark claims Zuckerberg/Facebook were responsible, while journalistic records (Vanity Fair) attribute the actions to the AJC and FBI.": 1,
    "Citation support is uncertain for https://www.voanews.com/a/east-asia-pacific_voa-news-china_chinese-statistics-reveal-plummeting-births-xinjiang-during/6203821.html.": 1,
    "Citation support is uncertain for https://www.remote-xuar.com/post/a-demographic-snapshot-of-xinjiang.": 1,
    "Lack of independent, third-party verification of the 1978 baseline of 5.55 million.": 1,
    "Absence of a unified, transparent methodology for the 2018/2020 population counts that resolves the 1-million-person discrepancy between Tianshannet and the Statistical Yearbook.": 1,
    "The Chinese government claims steady growth to 12m+ to deny genocide, while researchers using the government's own Statistical Yearbooks cite a 67% decline in natural population growth (2017-2019) as evidence of demographic genocide.": 1,
    "The government's claim of a birthrate of 'about 12' contradicts the ASPI/Guardian report of 68 per 1,000 in Kashgar (2014).": 1,
    "Lack of raw, year-by-year birthrate data for the Uighur population specifically from 2010-2017 to verify if '12' is a representative average or a cherry-picked figure from the end of the period.": 1,
    "The claim of a stable high birthrate contradicts the reported drop from 15.9 to 10.7 between 2017 and 2018.": 1,
    "The SSA projection assumes no replacement revenue, whereas the President's stated plan included replacement revenue from the general fund.": 1,
    "Citation support is uncertain for https://www.theguardian.com/world/2022/mar/24/cdc-coding-error-overcount-covid-deaths.": 1,
    "News reports claim the CDC recommended beard styles to fight coronavirus, while official CDC community guidance focuses on cloth masks that are unaffected by beards.": 1,
    "McSally voted to prevent Medicare from becoming a voucher program in 2015, but voted for a budget plan that would transition it to a voucher program in 2017.": 1,
    "Georgia allows regular ballots for these voters, while Arizona, Texas, and Ohio mandate provisional ballots.": 1,
    "Insufficient data on the exact percentage of states that allow regular vs. provisional ballots in this exact scenario.": 1,
    "California, Florida, and Pennsylvania allow regular ballots only upon surrender of the mail ballot, otherwise requiring provisional ballots.": 1,
    "Lack of a comprehensive federal guideline that applies to all 50 states regarding the 'should' of this action.": 1,
    "A Facebook user comment claims the IP addresses for the alleged hacked sites were in Ontario, Canada, contradicting the claim that they were Pakistani websites.": 1,
    "Resolve and cite the assertion: US President Trump opened a complaint platform to report censorship on Facebook, Twitter and YouTube.": 1,
    "Citation support is uncertain for https://www.whitehouse.gov/presidential-actions/2026/08/declaring-a-national-emergency-to-secure-the-united-states-bulk-power-system/.": 1,
    "Citation support is uncertain for https://www.usatoday.com/story/news/factcheck/2020/09/14/fact-check-list-10-donald-trump-accomplishments-3-true/3438025001/.": 1,
    "Citation support is uncertain for https://www.factcheck.org/2020/05/facebook-posts-distort-facts-on-trump-actions/.": 1,
    "Citation support is uncertain for https://www.cnbc.com/2020/04/13/trump-falsely-claims-authority-to-open-up-states-after-coronavirus.html.": 1,
    "Citation support is uncertain for https://politifact.com/factchecks/2020/apr/13/donald-trump/trumps-false-claim-its-him-not-governors-open-stat/.": 1,
    "Lack of ethnic-based wealth or income distribution data for the African continent.": 1,
    "Social media claims of Igbo wealth per capita contradict the official statement from the NBS that such a claim is 'not statistically correct' due to a lack of data.": 1,
    "Citation support is uncertain for https://guardian.ng/nigerian/what-is-the-richest-tribe-in-nigeria/.": 1,
    "Absence of state-level GDP data in Nigeria to allow for proxy calculations of regional wealth.": 1,
    "Lack of evidence regarding whether 'quality control' mentioned by Gen. Perna included any purity assays on commercial vaccine batches.": 1,
    "Citation support is uncertain for https://www.war.gov/News/News-Stories/Article/Article/2393298/military-to-play-logistics-only-role-in-covid-19-vaccine-effort/.": 1,
    "Citation support is uncertain for https://www.defensemedianetwork.com/stories/u-s-army-working-covid-19-vaccine-test-kit-validation/.": 1,
    "Gen. Perna claims 'distribution has begun' and the military's planning was 'crucial,' whereas Paul Mango (HHS) and the AP Fact Check state the federal military would not be involved in moving doses.": 1,
    "Resolve and cite the assertion: The US military will check purity": 1,
    "The claim asserts that 'anybody can go vote for anybody', but state law explicitly criminalizes voting in any name other than one's own.": 1,
    "Citation support is uncertain for https://www.usitc.gov/research_and_analysis/tradeshifts/2020/macroeconomic_conditions.htm.": 1,
    "The claim treats 33% (annualized) and 23.9% (quarterly) as comparable metrics of 'economic damage', which is statistically invalid.": 1,
    "Citation support is uncertain for https://www.siliconrepublic.com/careers/belfast-jobs-employers-workforce-tech-nation-uk-report.": 1,
    "Citation support is uncertain for https://politifact.com/factchecks/2020/jun/22/facebook-posts/no-evidence-tying-bill-gates-100-billion-covid-19/.": 1,
    "Resolve and cite the assertion: Masks lower immune systems.": 1,
    "Citation support is uncertain for https://theconversation.com/executive-order-on-vaccines-bypasses-an-evidence-based-process-that-has-kept-kids-safe-289469.": 1,
    "PMC7757609 reports leakage of airborne droplets through surgical masks even with a snug fit, whereas PMC7559551 reports surgical masks have a VFE of 98.5% to 99.9%.": 1,
    "Limited data comparing the passage of live, infectious virus particles versus simulated water droplets or bacteriophages (MS2) across all mask types.": 1,
    "Lack of a standardized medical definition for 'easily' in the context of viral passage.": 1,
    "The claim describes the event as a 'failure to appear' and a need to 'comply,' while the evidence describes it as a 'waived presence' and a 'requested delay' for legal counsel.": 1,
    "Citation support is uncertain for https://www.legalnewsline.com/northern-california-record/san-jose-church-seeks-scotus-intervention-on-covid-fines/article_b2a197cd-aee0-49ec-864c-c60c60d325d6.html.": 1,
    "Citation support is uncertain for https://www.capradio.org/articles/2020/09/02/claim-viewed-by-millions-on-social-media-says-california-legalized-pedophilia-that-is-false/.": 1,
    "Citation support is uncertain for https://factcheck.afp.com/fox-news-available-canada.": 1,
    "Verification of the 2002 baseline figure across multiple independent official sources.": 1,
    "Official SAPS personnel statistics for the specific year 2020 to match the runtime reference date.": 1,
    "The claim specifies a 50% growth, whereas a retrieved source claims an increase of 'over 65%' by 2012.": 1,
    "Resolve and cite the assertion: Since 2002, South Africa\u2019s police force has grown by 50%.": 1,
    "The claim uses financial year data (2017/18) but labels it as 'in 2018'.": 1,
    "The claim's numbers are incompatible with US 2018 police killing data, highlighting the necessity of the omitted jurisdiction (South Africa).": 1,
    "The claim does not specify the country, which is essential for the numbers to be accurate.": 1,
    "Citation support is uncertain for https://www.nature.org/en-us/about-us/where-we-work/united-states/oklahoma/stories-in-oklahoma/bison-history/.": 1,
    "Citation support is uncertain for https://apnews.com/article/archive-fact-checking-9325880707.": 1,
    "Citation support is uncertain for https://timesofindia.indiatimes.com/sports/cricket/ipl/top-stories/ipl-2020-suresh-raina-departure-adds-to-chennai-super-kings-woes/articleshow/77830053.cms.": 1,
    "Citation support is uncertain for https://www.newsweek.com/christian-site-raises-over-97k-kenosha-shooting-suspect-kyle-rittenhouse-after-other-crowdfunds-1528365.": 1,
    "NBC and AP label the event 'unprecedented,' while the AP record simultaneously quotes a source stating presidents have 'long conducted political and partisan activities from the White House.'": 1,
    "Absence of a comprehensive audit of all White House events prior to the 1940s to see if other nomination-related events occurred.": 1,
    "Lack of a formal, legal definition of 'purely political campaign event' to distinguish it from 'partisan activities.'": 1,
    "Citation support is uncertain for https://en.wikipedia.org/wiki/Kenosha_unrest.": 1,
    "Citation support is uncertain for https://www.reuters.com/business/energy/duterte-approves-inclusion-nuclear-power-philippine-energy-mix-2022-03-03/.": 1,
    "Citation support is uncertain for https://trumpwhitehouse.archives.gov/briefings-statements/president-donald-j-trump-combating-violence-protecting-americas-monuments-memorials-statues/.": 1,
    "Citation support is uncertain for https://www.poynter.org/fact-checking/2020/fact-checking-president-donald-trumps-2020-republican-national-convention-speech/.": 1,
    "The full transcripts provided by Rev.com and LA Times are incomplete and do not contain the quote, though the fact-checkers (who analyzed the full speech) do.": 1,
    "Citation support is uncertain for https://www.pbs.org/newshour/politics/rnc-day-4-fact-check-trumps-claims-about-covid-19-drug-prices-preexisting-conditions.": 2,
    "Lack of primary government documentation for the 'supplementary budget' mentioned by the Ize-Iyamu campaign team.": 1,
    "The 600 million naira claim is contradicted by the BudgIT analysis (417 million naira) and the Wikipedia table (900 million naira).": 1,
    "Absence of a verified source for the 900 million naira figure listed on Wikipedia.": 1,
    "Pence claims 'full resources' were marshalled, but Trump stated the federal government is 'not a shipping clerk' and governors reported competing against the federal government for supplies.": 1,
    "Pence claims a 'seamless partnership', but Trump explicitly told Pence not to call the governors of Washington and Michigan.": 1,
    "Citation support is uncertain for https://www.courthousenews.com/prosecutors-seek-to-ban-kyle-rittenhouse-from-bars-after-photos-emerge/.": 1,
    "Lack of direct evidence of membership in a recognized white supremacist organization beyond circumstantial 'consorting' claims.": 1,
    "Prosecutors' claims of 'consorting with white supremacists' vs. Rittenhouse's and his attorney's explicit denials of membership or affiliation.": 1,
    "Identification of the specific 'popular members of Congress' referenced by Pence.": 1,
    "The full Politifact verdict from the Free Press article is not present in the retrieved text.": 1,
    "Direct evidence comparing the specific policy platforms of those members to the socialism of the WWII era.": 1,
    "The provided full transcript of the RNC speech does not contain the exact quote found in the Politifact snippet.": 1,
    "Police Chief Miskinis claims there was no suggestion of criminal behavior at the time, whereas the ACLU and Lawyers for Civil Rights argue that police actively enabled armed civilians.": 1,
    "The provided records primarily focus on 2020 campaign positions and early administration actions; comprehensive official policy documents from 2022-2024 are missing.": 1,
    "Opponents define 'school choice' to include all alternatives to traditional public schools, while the Biden campaign defines it specifically as private vouchers that 'destroy our public schools'.": 1,
    "Trump claims he achieved energy independence; EIA data shows the U.S. remained a net energy exporter under Biden.": 1,
    "Trump claims Biden would end fracking; Biden's platform and public statements explicitly deny this.": 1,
    "Citation support is uncertain for https://www.snopes.com/fact-check/obama-spying-trump-campaign/.": 1,
    "Citation support is uncertain for https://www.jeelani-law.com/articles/limited-access-to-legal-counsel-in-biden-administrations-speedy-asylum-screenings.": 1,
    "Citation support is uncertain for https://cr.usembassy.gov/fact-sheet-president-biden-announces-new-actions-secure-border/.": 1,
    "Lack of a definitive current policy document on whether Biden supports a permanent, government-funded right to counsel for all undocumented immigrants versus continuing to rely on pro bono calls.": 1,
    "The term 'open borders' is used by political opponents to describe the administration's results, while the administration's official policy and executive actions (e.g., June 2024 proclamation) are explicitly designed to 'secure' and 'shut down' the border.": 1,
    "Primary sources (AP, Politico, Globe and Mail) include the qualifier 'we don't know that', while partisan sources (National Pulse, Federalist) omit it to present the statement as a confirmation.": 1,
    "Citation support is uncertain for https://apnews.com/article/elections-joe-biden-politics-china-asia-pacific-dcc0d1687d94753ba5bfaf82616fd17e.": 1,
    "Citation support is uncertain for https://thenationalpulse.com/archive-post/china-prefers-biden/.": 1,
    "Lack of a current (2024-2026) systematic review that reconciles the JHU estimates with the negative results from other RCTs and observational studies.": 1,
    "The JHU study (PMC11474081) claims CCP saved 16k-66k lives, whereas the Colorado Sun report and the Indian study (PMC8715228) report no evidence of benefit or no added benefit over other therapies.": 1,
    "Citation support is uncertain for https://pmc.ncbi.nlm.nih.gov/articles/PMC11474081/.": 1,
    "Insufficient data on the 'growing number of treatments' mentioned in the claim beyond the specific mention of CCP.": 1,
    "Citation support is uncertain for https://abc7news.com/post/not-real-news-untrue-stories-about-rnc-voting-from-this-week/6393856/.": 1,
    "Resolve and cite the assertion: The first night of the US Republican National Convention had 128.4 million viewers": 1
  },
  "mean_elapsed_seconds": 79.18214600000005,
  "total_searches": 2049,
  "total_page_fetches": 3953,
  "total_observed_tokens": 34452832,
  "token_usage_complete": false
}
```

### closed_book_execution

```json
{
  "metric_scope": "Local label-only metrics, NOT the official AVeriTeC evidence score",
  "predictions": {
    "n": 500,
    "accuracy": 0.538,
    "macro_f1": 0.4169183415163351,
    "coverage": 0.99,
    "selective_accuracy": 0.5434343434343434,
    "per_class": {
      "Supported": {
        "precision": 0.5606060606060606,
        "recall": 0.6065573770491803,
        "f1": 0.5826771653543307,
        "support": 122
      },
      "Refuted": {
        "precision": 0.8037383177570093,
        "recall": 0.5639344262295082,
        "f1": 0.6628131021194605,
        "support": 305
      },
      "Not Enough Evidence": {
        "precision": 0.1308411214953271,
        "recall": 0.4,
        "f1": 0.19718309859154926,
        "support": 35
      },
      "Conflicting Evidence/Cherrypicking": {
        "precision": 0.21428571428571427,
        "recall": 0.23684210526315788,
        "f1": 0.225,
        "support": 38
      }
    },
    "confusion_matrix": {
      "Supported": {
        "Supported": 74,
        "Refuted": 17,
        "Not Enough Evidence": 25,
        "Conflicting Evidence/Cherrypicking": 6,
        "ABSTAIN": 0
      },
      "Refuted": {
        "Supported": 39,
        "Refuted": 172,
        "Not Enough Evidence": 64,
        "Conflicting Evidence/Cherrypicking": 25,
        "ABSTAIN": 5
      },
      "Not Enough Evidence": {
        "Supported": 7,
        "Refuted": 12,
        "Not Enough Evidence": 14,
        "Conflicting Evidence/Cherrypicking": 2,
        "ABSTAIN": 0
      },
      "Conflicting Evidence/Cherrypicking": {
        "Supported": 12,
        "Refuted": 13,
        "Not Enough Evidence": 4,
        "Conflicting Evidence/Cherrypicking": 9,
        "ABSTAIN": 0
      }
    }
  },
  "failure_inclusive_predictions": {
    "n": 500,
    "accuracy": 0.538,
    "macro_f1": 0.4169183415163351,
    "coverage": 0.99,
    "selective_accuracy": 0.5434343434343434,
    "per_class": {
      "Supported": {
        "precision": 0.5606060606060606,
        "recall": 0.6065573770491803,
        "f1": 0.5826771653543307,
        "support": 122
      },
      "Refuted": {
        "precision": 0.8037383177570093,
        "recall": 0.5639344262295082,
        "f1": 0.6628131021194605,
        "support": 305
      },
      "Not Enough Evidence": {
        "precision": 0.1308411214953271,
        "recall": 0.4,
        "f1": 0.19718309859154926,
        "support": 35
      },
      "Conflicting Evidence/Cherrypicking": {
        "precision": 0.21428571428571427,
        "recall": 0.23684210526315788,
        "f1": 0.225,
        "support": 38
      }
    },
    "confusion_matrix": {
      "Supported": {
        "Supported": 74,
        "Refuted": 17,
        "Not Enough Evidence": 25,
        "Conflicting Evidence/Cherrypicking": 6,
        "ABSTAIN": 0
      },
      "Refuted": {
        "Supported": 39,
        "Refuted": 172,
        "Not Enough Evidence": 64,
        "Conflicting Evidence/Cherrypicking": 25,
        "ABSTAIN": 5
      },
      "Not Enough Evidence": {
        "Supported": 7,
        "Refuted": 12,
        "Not Enough Evidence": 14,
        "Conflicting Evidence/Cherrypicking": 2,
        "ABSTAIN": 0
      },
      "Conflicting Evidence/Cherrypicking": {
        "Supported": 12,
        "Refuted": 13,
        "Not Enough Evidence": 4,
        "Conflicting Evidence/Cherrypicking": 9,
        "ABSTAIN": 0
      }
    }
  },
  "verified": {
    "n": 500,
    "accuracy": 0.0,
    "macro_f1": 0.0,
    "coverage": 0.0,
    "selective_accuracy": null,
    "per_class": {
      "Supported": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "support": 122
      },
      "Refuted": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "support": 305
      },
      "Not Enough Evidence": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "support": 35
      },
      "Conflicting Evidence/Cherrypicking": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "support": 38
      }
    },
    "confusion_matrix": {
      "Supported": {
        "Supported": 0,
        "Refuted": 0,
        "Not Enough Evidence": 0,
        "Conflicting Evidence/Cherrypicking": 0,
        "ABSTAIN": 122
      },
      "Refuted": {
        "Supported": 0,
        "Refuted": 0,
        "Not Enough Evidence": 0,
        "Conflicting Evidence/Cherrypicking": 0,
        "ABSTAIN": 305
      },
      "Not Enough Evidence": {
        "Supported": 0,
        "Refuted": 0,
        "Not Enough Evidence": 0,
        "Conflicting Evidence/Cherrypicking": 0,
        "ABSTAIN": 35
      },
      "Conflicting Evidence/Cherrypicking": {
        "Supported": 0,
        "Refuted": 0,
        "Not Enough Evidence": 0,
        "Conflicting Evidence/Cherrypicking": 0,
        "ABSTAIN": 38
      }
    }
  },
  "execution_error_rate": 0.01,
  "stop_reasons": {
    "model_only_control": 495,
    "execution_error": 5
  },
  "verification_statuses": {
    "insufficient_evidence": 495,
    "execution_error": 5
  },
  "gap_counts": {},
  "mean_elapsed_seconds": 7.749926000000103,
  "total_searches": 0,
  "total_page_fetches": 0,
  "total_observed_tokens": 183416,
  "token_usage_complete": false
}
```

### citations

```json
{
  "total": 2611,
  "exact_quote": 1914,
  "reviewed": 1914,
  "exact_quote_but_jev_uncertain": 158,
  "exact_quote_but_jev_does_not_support": 34
}
```

### jev_relations

```json
{
  "supports": 1880,
  "unrelated": 27,
  "contradicts": 7
}
```

### human_audit_sample

```json
{
  "citation_rows": 454,
  "accepted_claims": 44,
  "rejected_claims": 50,
  "annotation_status": "Blank worksheet; independent human validation has not been performed"
}
```

Nonfatal matched-pair sensitivity: n=487, workflow-minus-control 14.37 percentage points, 95% paired bootstrap 9.45 to 19.10. This excludes operational failures post hoc; the primary denominator remains 500.

The resumed study also encountered cloud concurrent-slot timeouts and two pending control requests were interrupted by restarting the task-owned local Ollama daemon. All these failed attempts remain recorded. See runtime-incidents.json for recovery details; inference settings and source were unchanged.

Archive-aware host audit: 208/500 claims cite a host matching the gold fact-check article's host. This descriptive proxy does not prove exact-article exposure or exclude other exposure routes. The previous postprocessing missed Wayback-wrapped gold URLs; original metrics are preserved in study-metrics-original.json.

| Descriptive host group | Claims | Full prediction accuracy | Model-only accuracy |
|---|---:|---:|---:|
| host_match | 208 | 77.9% | 50.5% |
| no_host_match | 292 | 59.9% | 56.2% |

Groups are defined post hoc by workflow citations, not randomized conditions. An unmatched host does not establish no exposure, so this is not a contamination-free score or causal ablation.

## Interpretation limits

- This is a reused development split with current web access and no historical evidence cutoff, not a pristine held-out evaluation.
- The control comparison measures the combined prompting/retrieval/review workflow, not LangGraph's causal advantage over another framework.
- Policy and threshold variants replay identical evidence and assessments; they are not independent live ablations or validated optimal thresholds.
- NEI is excluded from decisive acceptance by design; accepted NEI recall is zero.
- Jev confidence and support relations are automated judgments, not human ground truth. The human audit remains unannotated.
- Reported tokens aggregate providers and are incomplete; they do not yield an exact billed cost.
- Claim-level intervals do not account for provider drift, current-web changes, correlated topics or resumption across a quota interruption.

## Reproducibility and outputs

study-metrics.json contains complete metrics and corrected host-audit provenance. per-claim-results.csv contains all 500 matched predictions and policy decisions. human-citation-audit.csv is blinded; keep human-audit-key.json separate from annotators. Manifest, source archive, dataset snapshot and JSONL outputs preserve the evaluated version.

Frozen inference hash: 624a8d2fa125aa3c82b5d4a8fc5f19da9c9a4e32040ee715e6245753459ac973. Dataset hash: 499793726b4a5406780928a3d9dedc48d6dd53de778f22437d129cacdb08e300.
