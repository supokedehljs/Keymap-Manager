# 发布到 GitHub

本文档记录 Keymap Manager 的版本更新、构建、验证、提交和 GitHub Release 流程。

## 1. 修改版本号

同时修改以下两个文件中的版本：

- `blender_manifest.toml`
- `__init__.py` 中的 `bl_info["version"]`

例如从 `0.1.1` 更新到 `0.1.2`：

```toml
version = "0.1.2"
```

```python
"version": (0, 1, 2),
```

然后在 `CHANGELOG.md` 中添加本次更新内容。

## 2. 构建 Blender 扩展

在 PowerShell 中运行：

```powershell
$repo = "C:\path\to\Keymap-Manager"
$blender = "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"

& $blender --factory-startup --command extension build `
  --source-dir $repo `
  --output-dir "$repo\release"
```

构建结果位于：

```text
release\keymap_manager-<version>.zip
```

## 3. 验证扩展包

```powershell
$zip = "$repo\release\keymap_manager-0.1.2.zip"

& $blender --factory-startup --command extension validate $zip
```

验证通过后，建议先在本机安装测试：

```powershell
& $blender --command extension install-file `
  -r user_default `
  -e `
  $zip
```

检查以下内容：

- 插件能在 Blender 5.3 中正常启用。
- “仅显示已修改”按钮显示在键位映射页面顶部。
- 修改、禁用和删除快捷键后能够正确过滤。
- Blender 重启后插件和设置仍然有效。

## 4. 提交到 Git

```powershell
cd $repo

git status
git add .
git commit -m "Release v0.1.2"
```

## 5. 推送到 GitHub

```powershell
git push origin main
```

如果当前分支不是 `main`：

```powershell
git branch -M main
git push -u origin main
```

如果 Git 要求登录，请使用浏览器登录 GitHub。不要把密码、Personal Access Token 或其他密钥保存到仓库文件中。

## 6. 创建 Git 标签

```powershell
git tag -a v0.1.2 -m "Keymap Manager v0.1.2"
git push origin v0.1.2
```

## 7. 创建 GitHub Release

1. 打开仓库页面：

   `https://github.com/supokedehljs/Keymap-Manager`

2. 点击右侧的 **Releases**。
3. 点击 **Draft a new release**。
4. 选择刚推送的标签，例如 `v0.1.2`。
5. 标题填写 `Keymap Manager v0.1.2`。
6. 把 `release\keymap_manager-0.1.2.zip` 上传为附件。
7. 根据 `CHANGELOG.md` 填写更新内容。
8. 点击 **Publish release**。

建议附件只上传 Blender 扩展 ZIP，不要上传 `__pycache__`、临时构建文件或个人配置。

## 8. 下次更新的最短流程

```powershell
# 1. 修改两个版本号，并更新 CHANGELOG.md

# 2. 构建
& $blender --factory-startup --command extension build `
  --source-dir $repo `
  --output-dir "$repo\release"

# 3. 验证
& $blender --factory-startup --command extension validate `
  "$repo\release\keymap_manager-<version>.zip"

# 4. 提交与推送
cd $repo
git add .
git commit -m "Release v<version>"
git push origin main

# 5. 标签
git tag -a v<version> -m "Keymap Manager v<version>"
git push origin v<version>

# 6. 到 GitHub 创建 Release 并上传 ZIP
```

