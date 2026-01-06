import { h, defineComponent } from "vue";
import { Icon } from "@iconify/vue";

/**
 * iconify 图标渲染钩子
 * @param icon 图标名称 (例如: ep:home-filled)
 * @param attrs 图标属性
 */
export function useRenderIcon(icon: string | any, attrs?: any) {
  // 如果传入的是对象（可能是已导入的组件），直接返回
  if (typeof icon === "object") {
    return icon;
  }
  
  // 返回一个函数式组件
  return defineComponent({
    name: "Icon",
    render() {
      return h(Icon, { icon, ...attrs });
    }
  });
}
