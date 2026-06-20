from solocoder_py.linear_regression import SimpleLinearRegression

true_w, true_b = 2.0, 1.0

for lr_val in [0.01, 0.05, 0.1]:
    for epochs in [1, 3, 5]:
        reg = SimpleLinearRegression(learning_rate=lr_val)
        for epoch in range(epochs):
            for x in range(-100, 100):
                y = true_w * x + true_b
                reg.update(float(x), y)
        print(f'lr={lr_val}, epochs={epochs}: w={reg.w:.4f} (err={abs(reg.w-true_w):.4f}), b={reg.b:.4f} (err={abs(reg.b-true_b):.4f})')

print()
reg2 = SimpleLinearRegression(learning_rate=0.1)
for x in range(-100, 100):
    y = -1.0 * x - 5.0
    reg2.update(float(x), y)
print(f'Neg slope: w={reg2.w:.4f} (expect -1), b={reg2.b:.4f} (expect -5)')
