import re
import math
import json

# Extract <answer> ... </answer> from the response


# Extract <tool_call> ... </tool_call> from the response
def extract_tool_call(response: str) -> list[str]:     
    matches = re.findall(r"<tool_call>(.*?)</tool_call>", response, re.DOTALL)
    return [m.strip() for m in matches]
    
def extract_numerical_answer(response: str) -> tuple[float, float]:
    pattern = r"\\boxed\{([^}]*)\}\s*\\pm\s*\\boxed\{([^}]*)\}"

    match = re.search(pattern, response)

    if match:
        mean = float(match.group(1))
        std = float(match.group(2))
        
        return mean, std
    else:
        return None, None


def chi2_pdf(x, df=15):
    if x < 0:
        return 0.0
    
    coef = 1.0 / ( (2 ** (df / 2.0)) * math.gamma(df / 2.0) )
    return coef * (x ** (df / 2.0 - 1.0)) * math.exp(-x / 2.0)


def nll_exclude_min(pred_mean, pred_std, true_mean, true_std = 0):

    if true_std <= 0:
        true_std = abs(true_mean) * 0.05

    if pred_std <= 0:
        pred_std = abs(pred_mean) * 0.01

    # Prevent division by zero and domain errors
    true_std = max(float(true_std), 1e-9)
    pred_std = max(float(pred_std), 1e-9)

    return (
        math.log(true_std / pred_std) +
        (pred_std**2 + (pred_mean - true_mean)**2) /
        (2 * true_std**2) -
        0.5
    )


def compute_score(solution_str, ground_truth, extra_info, alpha = 0.1):

    asked_time: str = extra_info.get("time_asked", "unknown_time") # "2023-12-31 00:00:00",

    tool_calls = extract_tool_call(solution_str)
    
    tool_call_score = chi2_pdf(len(tool_calls))
    
    answer = solution_str.split("</tool_call>")[-1].split("</think>")[-1] # crude way to get the answer part after the last tool call
    
    mean, std = extract_numerical_answer(answer)
    
    if mean is None or std is None:
        return {
            "tool_call_score": tool_call_score,
            "nll_score": -1,
            "total_score": -1,
            "error": "Failed to extract numerical answer"
        }
    
    gt_mean = ground_truth['mean']
    gt_std = ground_truth['std']

    raw_nll = nll_exclude_min(mean, std, gt_mean, gt_std)
    
    nll_score = max(- alpha * raw_nll + 1, -1)

    total_score = tool_call_score + nll_score

    print(f"### Extracted answer: mean={mean}, std={std}, ground_truth_mean={gt_mean}, ground_truth_std={gt_std}, nll_score={raw_nll}, tool_call_score={tool_call_score}, total_score={total_score}")
    
    return {
        "tool_call_score": tool_call_score,
        "nll_score": nll_score,
        "total_score": total_score
    }