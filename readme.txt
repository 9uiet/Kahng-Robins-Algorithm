Kahng-Robins-Algorithm
======================

简介
----
本项目实现了Kahng/Robins 1-Steiner插入算法，用于在网格上进行Steiner路由。
提供基础版本与基于Hanan网格的优化版本，并支持输出路由结果与SVG可视化。

文件说明
--------
- steiner_routing.py：基础KR算法实现。
- steiner_routing_hanan.py：基于Hanan网格并缓存距离的加速版本。
- *.nets：示例输入文件。

输入格式（.nets）
---------------
首行："<grid_size> <net_count>"
后续每行："<net_name> [ (x1,y1) (x2,y2) ... ]"
坐标为1-based。

运行方式
--------
python steiner_routing.py <input.nets>
python steiner_routing_hanan.py <input.nets>

输出结果
--------
- <input>.routing：路由线段结果。
- <input>/：与输入同名的目录，内含整体SVG与每个net的SVG。

说明
----
算法会计算总线长并在控制台输出每个net的线长、总线长、运行时间和内存占用。
