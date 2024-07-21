import networkx as nx
from collections import deque
import matplotlib.pyplot as plt

# 创建一个7x7的二维网格图
G = nx.grid_2d_graph(7, 7)

# 删除一些边和节点，使得某些中间点只有2条边
G.remove_edge((3, 3), (3, 4))
G.remove_edge((3, 3), (4, 3))

# 确保节点数为49
assert G.number_of_nodes() == 49

# 从节点(4,3)开始进行深度为2的广度遍历
start_node = (4, 3)
depth_limit = 2

# 使用一个队列来存储待访问的节点和它们的深度
queue = deque([(start_node, 0)])

# 使用一个集合来存储已经访问过的节点
seen = set()

# 存储遍历的边
edges = []

while queue:
    node, depth = queue.popleft()
    if depth > depth_limit:
        break
    if node not in seen:
        seen.add(node)
        for neighbor in G.neighbors(node):
            if neighbor not in seen:
                edges.append((node, neighbor))
            queue.append((neighbor, depth + 1))

# 画出图及遍历的线
pos = nx.spring_layout(G)
nx.draw(G, pos, with_labels=True)
nx.draw_networkx_edges(G, pos, edgelist=edges, edge_color='r', width=2)
plt.show()