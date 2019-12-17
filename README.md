# spider
> 根据用户名爬取instagram网站的数据

## Example Usage

1. 安装依赖包
    ```
    pip install -r requirements.txt
    ```
    + 可以使用virtualenv创建环境
2. 运行

    ```
    python instagram.py --name test --proxy 127.0.0.1:1080 --sleep 1
    ```
3. 注意项
    + 数据存放在 {name}.json文件中
    + 如果爬取意外过程中,异常中断,会记录游标到{name}.log中
    + 因为有可能发生异常退出,断点恢复会导致一部分数据有重复.可使用: `cat name.json|sort|uniq > name.json` 去重
