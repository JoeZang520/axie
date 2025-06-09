def play_zeal(self, zeal_count=1):
        """使用zeal卡"""
        try:
            # 检查能量是否足够
            if self.energy < zeal_count:
                print(f"[ERROR] 能量不足，需要{zeal_count}点能量，当前能量: {self.energy}")
                return False
                
            # 检查碎片是否足够
            if self.fragments < zeal_count:
                print(f"[ERROR] 碎片不足，需要{zeal_count}个碎片，当前碎片: {self.fragments}")
                return False
                
            # 使用zeal卡
            for i in range(zeal_count):
                print(f"[INFO] 正在使用第{i+1}/{zeal_count}张zeal卡")
                if not self.use_card("zeal"):
                    print(f"[ERROR] 第{i+1}次使用zeal卡失败")
                    return False
                print(f"[INFO] 第{i+1}张zeal卡使用成功")
                time.sleep(0.5)  # 等待动画完成
                
            # 更新能量和碎片
            self.energy -= zeal_count
            self.fragments -= zeal_count
            print(f"[INFO] 使用完{zeal_count}张zeal卡后，剩余能量: {self.energy}，剩余碎片: {self.fragments}")
            
            # 等待动画完成
            time.sleep(1)
            
            # 检查是否需要保留卡片
            if self.energy > 0 and self.fragments > 0:
                # 使用灰度图像检测卡片
                if self.find_card("zeal", use_grayscale=True):
                    print("[INFO] 检测到zeal卡，尝试保留")
                    if not self.keep_card("zeal"):
                        print("[ERROR] 保留zeal卡失败")
                        return False
                    print("[INFO] zeal卡保留成功")
                    time.sleep(0.5)  # 等待保留动画完成
                else:
                    print("[INFO] 未检测到zeal卡，无需保留")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 使用zeal卡时发生错误: {str(e)}")
            return False 