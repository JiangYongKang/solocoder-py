from solocoder_py.linear_regression import SimpleLinearRegression
import random

true_w = 2.0
true_b = 3.0

print("=== Per-component clipping on perfect data ===")
for lr in [0.01, 0.05, 0.1]:
    for clip_val in [1.0, 5.0, 10.0]:
        reg = SimpleLinearRegression(lr, clip_value=clip_val)
        for x in range(1000):
            reg.update(float(x), true_w * x + true_b)
        r2 = reg.r2_score()
        w_err = abs(reg.w - true_w) / true_w * 100
        b_err = abs(reg.b - true_b) / true_b * 100
        print(f"lr={lr}, clip={clip_val}: w={reg.w:.4f} ({w_err:.1f}%), b={reg.b:.4f} ({b_err:.1f}%), R2={r2:.6f}")

print("\n=== Per-component clipping on random noise ===")
random.seed(42)
for lr in [0.001, 0.01, 0.1]:
    for clip_val in [1.0, 5.0, 10.0]:
        reg = SimpleLinearRegression(lr, clip_value=clip_val)
        for _ in range(5000):
            x = random.uniform(0, 100)
            y = random.uniform(0, 100)
            reg.update(x, y)
        r2 = reg.r2_score()
        print(f"lr={lr}, clip={clip_val}: R2={r2:.6f}, w={reg.w:.4f}, b={reg.b:.4f}")
