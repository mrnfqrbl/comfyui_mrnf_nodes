
import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: 'mrnf.图像加载API',
    nodeCreated: async function (node) {
        if (node?.comfyClass === "图像加载API") {
            console.log("图像加载API 节点已创建，开始添加 UI...");

            // 移除节点标题
            node.title = "";
            node.title_widgets = [];

            // 查找 base64_图像 Widget
            let base64_图像 = node.widgets.find(w => w.name === "base64_图像");

            // 如果找不到 base64_图像 Widget，则创建一个
            if (!base64_图像) {
                base64_图像 = node.addWidget("text", "base64_图像", "", (s) => { }, {});
                base64_图像.name = "base64_图像";
            }

            // 隐藏 base64_图像 输入框 (可选)
            // base64_图像.element.style.display = "none";

            // 创建预览图像元素
            const img = document.createElement("img");
            img.style.width = "200px";
            img.style.height = "auto";
            img.style.marginTop = "5px";
            img.style.border = "1px solid #ccc";
            img.style.objectFit = "contain"; // 保持图像比例
            node.addDOMWidget("image_preview", "image", img, {
                name: "预览",
                get value() {
                    return this.src;
                },
                set value(v) {
                    this.src = v;
                },
            });
            node.img = img;

            // 定义按钮 Widget
            const buttonWidget = {
                type: "button",
                name: "选择文件",
                callback: () => {
                    console.log("按钮回调被触发");

                    const fileInput = document.createElement("input");
                    fileInput.type = "file";
                    fileInput.accept = "image/*";

                    fileInput.addEventListener("change", (event) => {
                        const file = event.target.files[0];
                        if (file) {
                            const reader = new FileReader();
                            reader.onload = (e) => {
                                const base64String = e.target.result;


                                // 设置 base64_图像 Widget 的值
                                base64_图像.element.style.display = "none";
                                base64_图像.value = base64String; // 直接修改 value
                                base64_图像.callback(base64String); // 触发回调，传递最新的 Base64 字符串
                                base64_图像.element.value = base64String; // 更新输入框的显示值

                                // 更新预览图像
                                node.img.src = base64String;

                                // 强制刷新节点显示
                                app.graph.setDirtyCanvas(true);
                            };
                            reader.onerror = (error) => {
                                console.error("读取文件失败:", error);
                                alert("读取文件失败，请检查文件是否损坏或权限是否正确。");
                            };
                            reader.readAsDataURL(file); // 读取为 Data URL (Base64)
                        }
                    });

                    fileInput.click();
                }
            };

            node.addCustomWidget(buttonWidget);
            console.log("按钮已添加到节点");
        }
    }
});
