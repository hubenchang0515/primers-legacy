# Primers - Learn to Program From Scratch

!class: notification is-info has-text-light
欢迎来到 Primers ———— 你的编程学习伙伴。

Primers 致力于为各类编程学习者提供全面、系统的编程教程和实践资源。无论你是编程新手，还是有一定基础的开发者，Primers 都提供了适合的学习路径和丰富的实战项目，帮助你从零开始，逐步掌握编程技能，成为一名优秀的开发者。

**Primers 的特色**：
* **全面的知识体系**：覆盖Python~~、JavaScript、Java、C++、前端、后端~~等多个技术栈，适合各个阶段的学习者。
* **实战项目驱动**：理论与实践相结合，每个课程都配有实际项目，帮助你巩固知识，解决实际问题。
* **互动式学习体验**：提供[在线编程环境](https://hubenchang0515.github.io/shift/)、社区互动和答疑支持，解决你的学习疑惑。
* **自主学习进度**：灵活的学习方式，可以根据个人节奏安排学习计划，随时随地进行学习。
* **跨平台学习支持**：无论你是在电脑、手机还是平板上学习，Primers 都能无缝适配，确保你随时随地都可以进行学习，充分利用碎片时间，提升效率。

## 在线编程环境

Primers 基于 [Shift](https://github.com/hubenchang0515/shift) 提供在线编程环境，这是一个示例:  

```python shift 10
def generate_yanghui_triangle(rows):
    """
    生成杨辉三角的前 rows 行。
    
    :param rows: 杨辉三角的行数
    :return: 一个列表，包含杨辉三角的行
    """
    triangle = []
    for i in range(rows):
        # 初始化当前行
        row = [1] * (i + 1)
        # 填充非边界的值
        for j in range(1, i):
            row[j] = triangle[i - 1][j - 1] + triangle[i - 1][j]
        triangle.append(row)
    return triangle

def print_yanghui_triangle(triangle):
    """
    打印杨辉三角。
    
    :param triangle: 杨辉三角的列表
    """
    max_width = len(" ".join(map(str, triangle[-1])))  # 计算最后一行的宽度
    for row in triangle:
        row_str = " ".join(map(str, row))
        print(row_str.center(max_width))

# 示例：生成并打印前 10 行的杨辉三角
rows = int(input("Please Input Rows: "))
yanghui_triangle = generate_yanghui_triangle(rows)
print_yanghui_triangle(yanghui_triangle)
```