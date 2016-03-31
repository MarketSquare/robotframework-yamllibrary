# robotframework-yamllibrary
安装：
方法1：联网，sudo pip install robotframework-yamllibrary;
方法2：从github这里，或者从pypi.python.org/pypi/robotframework-yamllibrary下面下载tar包，然后sudo pip install tar包;
方法3：下载并解压tar包，拷贝YamlLibrary目录到Lib/site-packages下（windows），或到dist-packages/下（linux）。Linux下也可以不实际拷贝，创建link即可;

使用：Robot/RIDE里直接装载，以YamlLibrary作为库名字

关键字举例:
```robotframework
${a}	Get Tree	${yaml_string}	icmp.types%type=5%rate_limit.pps
${b}	Get Tree	${yaml_string}	bpf%name~^2[0-9]{7}_[0-9a-f]{32}%ratelimit.pps
Nodes Should Match	${yml_string}	bpf/action=ratelimit/ratelimit.pps	112001 > x >= 112000
Nodes Should Match	${yml_string}	bpf/action=ratelimit/name	~^2[0-9]{7}_[0-9a-f]{32}$
```

说明：
基本思想是按文档树的路径返回子树（这里的子树也可以是一个节点，所以Get Tree也可以用于返回单个节点的值），或递归地对子树的键/值做匹配比较。文档树的路径以字典的键为字段上下级之间用小数点连接而成，对于键相同的数组元素以数组下标（从0开始）取代键。比如 student.grades.2.classes.0.wangdan.age就是一个路径, 表明三年纪一班王丹的年龄. 如要不能确定数组下标，可以使用path_left/sub_path=xxx/path_right匹配法下沉到其子元素定位出，需要材料：一段承接path_left的子路径（两头不加小数点），一个匹配符号（=表示需相等，~表示需正则匹配），一个值串。这三个部分匹配得到的数组项应该是唯一的（由使用者写好这三部分确保这个唯一性）。下沉定位法允许在一个路径里多次使用。

使用的时候，先读取数据库或者web接口测试得到json或者yaml文档到内存（python字典或者list），当作参数1。然后可以用上面两个关键字找出指定路径（参数2）的子文档树或者节点值（节点是一个单node的文档）。参数3给出一个同类型文档树用于给出期望的节点键/值或值比较方式（值比较方式有相等=，正则表达式匹配～，和数学不等式）。Nodes Should Match 关键字会递归地遍历参数3文档树，全部键都存在且值都符合期望才会返回True，任意一个不满足就会退出并返回False。


Debug：Set Log Level为Debug可以得到带debug的log，展开就可以看到出错的地方
