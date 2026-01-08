"""
Yadisk команды
"""
from telegram import Update
from telegram.ext import ContextTypes
import logging

log = logging.getLogger(__name__)

async def yadisk_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /yadisk_list - список файлов на Яндекс.Диске"""
    try:
        from yandex_disk_helper import list_files, get_disk_info, format_file_size, get_file_type
        
        await update.message.reply_text("⏳ Получаю список файлов с Яндекс.Диска...")
        
        # Получаем информацию о диске
        disk_info = await get_disk_info()
        
        # Получаем список файлов
        path = " ".join(context.args) if context.args else "/"
        result = await list_files(path=path, limit=50)
        
        if not result:
            await update.message.reply_text("❌ Не удалось получить список файлов")
            return
        
        items = result.get("_embedded", {}).get("items", [])
        
        if not items:
            await update.message.reply_text(
                f"📂 *Яндекс.Диск*\n\n"
                f"Папка `{path}` пуста",
                parse_mode='Markdown'
            )
            return
        
        # Формируем сообщение
        text = f"📂 *Яндекс.Диск*\n\n"
        
        if disk_info:
            total = disk_info.get("total_space", 0) / (1024**3)
            used = disk_info.get("used_space", 0) / (1024**3)
            text += f"💾 Занято: {used:.1f} ГБ из {total:.1f} ГБ\n\n"
        
        text += f"📁 Путь: `{path}`\n"
        text += f"Файлов: {len(items)}\n\n"
        
        # Группируем по типу
        folders = [item for item in items if item.get("type") == "dir"]
        files = [item for item in items if item.get("type") == "file"]
        
        # Показываем папки
        if folders:
            text += "*📁 Папки:*\n"
            for folder in folders[:10]:
                name = folder.get("name", "")
                text += f"  • {name}/\n"
            if len(folders) > 10:
                text += f"  _...и еще {len(folders) - 10} папок_\n"
            text += "\n"
        
        # Показываем файлы
        if files:
            text += "*📄 Файлы:*\n"
            for file in files[:15]:
                name = file.get("name", "")
                size = format_file_size(file.get("size", 0))
                file_type = get_file_type(name)
                
                type_emoji = {
                    'document': '📝',
                    'spreadsheet': '📊',
                    'presentation': '📈',
                    'image': '🖼',
                    'archive': '📦',
                    'code': '💻',
                    'other': '📄'
                }.get(file_type, '📄')
                
                # Обрезаем длинные имена
                if len(name) > 30:
                    name = name[:27] + "..."
                
                text += f"  {type_emoji} {name} • {size}\n"
            
            if len(files) > 15:
                text += f"  _...и еще {len(files) - 15} файлов_\n"
        
        text += f"\n💡 Используйте:\n"
        text += f"• `/yadisk_search [запрос]` - поиск файлов\n"
        text += f"• `/yadisk_recent` - последние файлы"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        log.error(f"❌ Ошибка получения файлов: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def yadisk_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /yadisk_search - поиск файлов на Яндекс.Диске"""
    if not context.args:
        await update.message.reply_text(
            "🔍 *Поиск на Яндекс.Диске*\n\n"
            "Использование: `/yadisk_search [запрос]`\n\n"
            "Примеры:\n"
            "• `/yadisk_search договор`\n"
            "• `/yadisk_search КП`\n"
            "• `/yadisk_search .pdf`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from yandex_disk_helper import search_files, format_file_size, get_file_type
        
        query = " ".join(context.args)
        
        await update.message.reply_text(f"🔍 Ищу файлы: *{query}*...", parse_mode='Markdown')
        
        files = await search_files(query, limit=50)
        
        if not files:
            await update.message.reply_text(
                f"🔍 Поиск: *{query}*\n\n"
                f"❌ Файлов не найдено",
                parse_mode='Markdown'
            )
            return
        
        text = f"🔍 *Найдено: {len(files)} файлов*\n\n"
        text += f"Запрос: `{query}`\n\n"
        
        for i, file in enumerate(files[:20], 1):
            name = file.get("name", "")
            size = format_file_size(file.get("size", 0))
            path = file.get("path", "")
            file_type = get_file_type(name)
            
            type_emoji = {
                'document': '📝',
                'spreadsheet': '📊',
                'presentation': '📈',
                'image': '🖼',
                'archive': '📦',
                'code': '💻',
                'other': '📄'
            }.get(file_type, '📄')
            
            # Обрезаем длинные имена
            display_name = name[:35] + "..." if len(name) > 35 else name
            
            text += f"{i}. {type_emoji} {display_name}\n"
            text += f"   {size} • `{path}`\n\n"
        
        if len(files) > 20:
            text += f"_...и еще {len(files) - 20} файлов_\n\n"
        
        text += f"💡 Для скачивания используйте путь файла"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        log.error(f"❌ Ошибка поиска: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def yadisk_recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /yadisk_recent - последние файлы на Яндекс.Диске"""
    try:
        from yandex_disk_helper import get_recent_files, format_file_size, get_file_type
        from datetime import datetime
        
        await update.message.reply_text("⏳ Получаю последние файлы...")
        
        files = await get_recent_files(limit=20)
        
        if not files:
            await update.message.reply_text("❌ Файлов не найдено")
            return
        
        text = f"🕐 *Последние файлы* (топ-{len(files)})\n\n"
        
        for i, file in enumerate(files, 1):
            name = file.get("name", "")
            size = format_file_size(file.get("size", 0))
            modified = file.get("modified", "")
            file_type = get_file_type(name)
            
            type_emoji = {
                'document': '📝',
                'spreadsheet': '📊',
                'presentation': '📈',
                'image': '🖼',
                'archive': '📦',
                'code': '💻',
                'other': '📄'
            }.get(file_type, '📄')
            
            # Форматируем дату
            try:
                dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                date_str = dt.strftime("%d.%m.%Y %H:%M")
            except:
                date_str = modified
            
            # Обрезаем длинные имена
            display_name = name[:30] + "..." if len(name) > 30 else name
            
            text += f"{i}. {type_emoji} {display_name}\n"
            text += f"   {size} • {date_str}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        log.error(f"❌ Ошибка получения файлов: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
