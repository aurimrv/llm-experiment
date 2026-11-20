#!/usr/bin/env Rscript
# Confirm the rank correlation between unique test cases and mutation score.
# The Python script writes data/model-summary.csv. Run this from anywhere:
#   Rscript analysis/factorial-models/analyze_models.R

args <- commandArgs(trailingOnly = TRUE)
root <- if (length(args) >= 1) args[[1]] else Sys.getenv("PWD")
summary_path <- file.path(root, "analysis", "factorial-models", "data", "model-summary.csv")
if (!file.exists(summary_path)) {
  summary_path <- file.path("data", "model-summary.csv")
}
if (!file.exists(summary_path)) {
  stop("model-summary.csv was not found. Run analyze_models.py first.")
}

models <- read.csv(summary_path, stringsAsFactors = FALSE)
test <- cor.test(models$unique_tests, models$mutation_score, method = "spearman", exact = FALSE)

out_dir <- dirname(summary_path)
result <- data.frame(
  x = "unique_tests",
  y = "mutation_score",
  rho = unname(test$estimate),
  statistic = unname(test$statistic),
  p_value = test$p.value,
  n = nrow(models),
  method = test$method
)
write.csv(result, file.path(out_dir, "spearman-r.csv"), row.names = FALSE)
message(sprintf("Spearman rho = %.4f, p = %.4g, n = %d", result$rho, result$p_value, result$n))
message("Wrote ", file.path(out_dir, "spearman-r.csv"))
