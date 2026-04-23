// 极简直播解析webview.js 直接取流播放、隐藏网页
(function(){
    // 1.隐藏网页所有多余元素、去掉页面布局
    document.body.innerHTML = "";
    document.body.style.background = "#000";
    document.documentElement.style.overflow = "hidden";

    // 2.抓取页面内视频标签
    let video = document.querySelector("video");
    if(!video){
        let videos = document.querySelectorAll("video");
        video = videos[0];
    }

    // 3.强制自动播放 + 全屏
    if(video){
        video.controls = true;
        video.style.width = "100vw";
        video.style.height = "100vh";
        video.style.position = "fixed";
        video.style.left = "0";
        video.style.top = "0";
        video.play();
        
        // 调用原生APP全屏
        if(window.AndroidJSBridge){
            AndroidJSBridge.fullScreen();
        }
    }

    // 4.拦截跳转、屏蔽广告、屏蔽弹窗
    window.open = function(){return null;};
    document.querySelectorAll("a,div[ad],.ads").forEach(el=>el.remove());
})();
