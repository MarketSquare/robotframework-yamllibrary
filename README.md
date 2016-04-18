如果你需要使用树型的json或者yaml字符串而不是字典，比如读取或者定义大量变量，一次性比较很多变量等，YamlLibrary是一个好的选择。 Get Tree接受一个字符串和一个路径作为参数，将字符串转成yaml树（注意json是yaml的子集，所以也可以用）然后返回给定路径下的子树（注意节点值是最小的子树，所以可以用来取节点值）。Node should Match则在Get Tree的基础上增加一个动作：将取出来的子树跟第三个参数--一个描述比较期望值的子树，一次性完成全部比较。

# robotframework-yamllibrary
安装：
拷贝到Lib/site-packages下（windows），或者创建link到dist-packages/下（linux）

使用库：Robot里直接装载YamlLibrary库名字

关键字举例:
```robotframework
${a}	Get Tree	${yaml_string}	icmp.types.0.rate_limit.pps
${a}	Get Tree	${yaml_string}	icmp.types/type=5/rate_limit.pps
${b}	Get Tree	${yaml_string}	bpf.2.ratelimit.pps
${b}	Get Tree	${yaml_string}	bpf/user.name~^2[0-9]{7}_[0-9a-f]{32}/ratelimit.pps
Nodes Should Match	${yml_string}	bpf/action=ratelimit/ratelimit.pps	112001 > y >= 112000
Nodes Should Match	${yml_string}	bpf/action=ratelimit/user.name~^2[0-9]{7}_[0-9a-f]{32}$
Nodes Should Match	${yml_string}	bpf/action=ratelimit/2
```

说明：
读取数据库或者web接口测试得到json或者yaml文档（参数1），然后可以用上面两个关键字读取路径（参数2）下的子文档/值，以及对值进行比较（参数3）。值比较的方式有相等=，正则表达式匹配～，和数学表达式（不等式，y作变量）。全部比较成功才会返回True，否则False。

路径以小数点分割，碰到数组元素则用数字下标（从0开始）。
对于有多个同级的元素形成的列表，需要确定数组下标，这里采取下沉到其子元素定位的办法：用/或者%分割的一段子路径（相对路径，小数点分割），一个=或～符号，一个比较值，这三个部分匹配得到所在数组的下标应该是唯一的（由使用者写好这三部分确保这个唯一性）。注意路径比较的时候是不可以用数学表达式

Debug：Set Log Level为Debug可以得到带debug的log，展开就可以看到出错的地方
