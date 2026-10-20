# 九寨沟全景漫游网页

## 文件
- `index.html`：完整网页，可直接用于 GitHub Pages。
- `README.md`：部署与素材说明。

## 功能
- 五花海横向全景拖动查看、缩放、重置视角、全屏。
- 切换长海、五彩池、珍珠滩瀑布、诺日朗瀑布。
- 普通照片场景支持拖动与缩放；网页明确区分普通照片与 360° 全景。
- 手机与电脑响应式布局。

## 部署到 GitHub Pages
1. 新建 GitHub 仓库，例如 `jiuzhaigou-360`。
2. 将 `index.html` 和本 `README.md` 上传到仓库根目录。
3. 打开仓库 `Settings → Pages`。
4. 在 `Build and deployment` 中选择 `Deploy from a branch`。
5. Branch 选择 `main`，目录选择 `/(root)`，点击 Save。
6. 等待部署后点击 Pages 页面显示的站点地址。

## 重要素材说明
当前提供的五花海图片是一张横向全景照片（长宽比约 5.34:1），可以进行横向环视，但不是完整球形的 360° VR 全景。其他景点当前为普通照片，支持缩放和拖动查看，不冒充 360° 全景。

五花海全景：
- 图片：九寨沟五花海全景 Jiuzhaigou Five Flower Lake Panorama.jpg
- 作者：George Lu
- 来源：https://commons.wikimedia.org/wiki/File:九寨沟五花海全景_Jiuzhaigou_Five_Flower_Lake_Panorama.jpg
- 许可：CC BY 2.0 https://creativecommons.org/licenses/by/2.0/
- 网页使用时应保留作者、来源和许可链接。

其他照片来源与许可：
- 长海：https://commons.wikimedia.org/wiki/File:Long_Lake_Jiuzhaigou.jpg （Jean-Marie Hullot；使用时请核对文件页许可）
- 五彩池：https://commons.wikimedia.org/wiki/File:九寨溝五彩池_Jiuzhaigou_Wucaichi_Lake_-_panoramio.jpg （lienyuan lee；CC BY 3.0）
- 珍珠滩瀑布：https://commons.wikimedia.org/wiki/File:九寨溝珍珠灘瀑布_Jiuzhaigou_Pearl_Shoal_Falls_-_panoramio.jpg （lienyuan lee；CC BY 3.0）
- 诺日朗瀑布：https://commons.wikimedia.org/wiki/File:Jiuzhaigou_Waterfall.jpg （Gjl；GFDL）

## 网络依赖
Pannellum 通过 jsDelivr CDN 加载，图片来自 Wikimedia Commons。网页发布后需要联网访问。部分 Wikimedia 图片文件名或缩略图地址可能因服务器重定向而变化；如果某张普通照片未显示，可通过上方来源页查看并更新链接。
