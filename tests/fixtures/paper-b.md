# Synthetic Study B: Calibration in a Cold Field Task

SYNTHETIC TEST FIXTURE — not a real publication. Author and DOI are not supplied. Year: 2026.

## Abstract

A synthetic cold field classification task compares fixed and adaptive calibration. Adaptive calibration has a lower descriptive score in this setting.

## Question

Does adaptive calibration improve macro-F1 over the fixed baseline on this cold field task?

## Methods

Twelve synthetic field sequences from one cold test site are paired between configurations. The outcome is macro-F1. These sequences and labels differ from the controlled sensor task of Study A. Only descriptive means are reported; no uncertainty interval or significance test is provided.

## Results

| Configuration | Mean macro-F1 |
| --- | --- |
| Fixed baseline | 0.72 |
| Adaptive | 0.68 |

The adaptive mean is lower by 0.04 macro-F1 units. This result alone does not establish population-level inferiority.

## Discussion

The authors recommend testing the conditions in which adaptation helps rather than assuming a universal improvement. This task is not numerically interchangeable with accuracy on a different dataset.

## Limitations

One synthetic site and twelve paired sequences restrict generalization. The study does not establish a causal explanation for the lower score.

## References

No external works supplied.

## Appendix: Reference-style and HTML images

These two references intentionally point to the same supplied image, not two independent experiments. The graphic illustrates controlled-condition accuracy in Study A, not this paper's macro-F1 result.

![Illustrative controlled comparison][controlled]

[controlled]: figures/controlled.png

<img src="figures/controlled.png" alt="The same illustrative controlled comparison" />
