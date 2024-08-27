from PyQt5 import QtWidgets, QtCore, uic
from PyQt5.QtWidgets import QFileDialog, QWidget, QHBoxLayout, QStackedWidget, QApplication
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
#Первое (Импортируем классы наших файлов, которые находятся в папке py_windows)
from py_windows.mainScreen import Ui_MainWindow
import sys
import os
from PyQt5.QtGui import QColor, QIcon



import psycopg2
from psycopg2 import Error


from mutagen import File
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3



#Вторым делом создаём класс для нашего окна (Которое мы делали в qtDesigner)
class Main_Screen(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(Main_Screen, self).__init__(parent)
        self.setupUi(self)


    
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)

        self.player = QMediaPlayer()
        self.main_screen = Main_Screen()
        self.main_screen.pushButton_3.clicked.connect(self.add_music)
        self.main_screen.pushButton.clicked.connect(self.playAudio)
        self.main_screen.pushButton_2.clicked.connect(self.pauseAudio)
        self.main_screen.pushButton_4.clicked.connect(self.remove_music)


        self.player.positionChanged.connect(self.update_slider)
        self.player.durationChanged.connect(self.update_duration)


        self.player.mediaStatusChanged.connect(self.media_status_changed) #######

        self.main_screen.horizontalSlider.sliderMoved.connect(self.set_position)
        self.load_music_from_db()


        self.stack = QStackedWidget()
        self.stack.addWidget(self.main_screen)

        self.stack.setCurrentIndex(0)
        self.nameProgramm(self.stack.currentIndex())


        self.gotomain()

        hbox = QHBoxLayout(self.centralWidget)
        hbox.setContentsMargins(0, 0, 0, 0) #вроде можно без этого ????????????????????????????????????
        hbox.addWidget(self.stack)

    def nameProgramm(self, w=0):
        self.setWindowTitle('SoundWave')
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_path, 'images', 'logo2.png')
        self.setWindowIcon(QIcon(icon_path))


    def gotomain(self):
        self.stack.setCurrentIndex(0)
        self.nameProgramm(self.stack.currentIndex())

    def add_music(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Выберите аудиофайлы", "", "Audio Files (*.mp3 *.wav *.ogg)")
        if files:
            for file in files:
                audio = File(file, easy=True)  # Получаем объект аудиофайла с метаданными
                if audio:
                    title = os.path.basename(file)  # Название файла по умолчанию
                    artist = audio.get('artist', ['Unknown Artist'])[0]  # Извлекаем артиста, если есть
                    album = audio.get('album', ['Unknown Album'])[0]    # Извлекаем альбом, если есть
                else:
                    # Если метаданные не найдены, используем имя файла и пустые строки
                    title = os.path.basename(file)
                    artist = "Unknown Artist"
                    album = "Unknown Album"
                    
                if not self.music_exists_in_db(title, file):
                    self.main_screen.listWidget.addItem(title)
                    self.add_music_from_db(title, artist, album, file)
        else:
            # Если музыка уже существует, игнорируем добавление
            print(f"Музыка '{title}' уже существует в базе данных.")

    def music_exists_in_db(self, title, file):
        conn = self.connectt()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM music WHERE title = %s AND file_path = %s", (title, file))
        result = cur.fetchone()[0]
        cur.close()
        conn.close()
        return result > 0  # Возвращает True, если такая музыка уже существует

    def remove_music(self):
        current_item = self.main_screen.listWidget.currentItem()
        if current_item:
            file_path = current_item.text()
            path = self.load_path_music_to_delete_and_play(file_path)

            current_media_path = self.player.currentMedia().canonicalUrl().toLocalFile()
            if path == current_media_path:
                self.player.stop()
                self.main_screen.label.clear()

            self.main_screen.listWidget.takeItem(self.main_screen.listWidget.row(current_item))
            self.remove_music_from_db(path)
            self.play_next_audio()



    def playAudio(self):

        if self.player.state() == QMediaPlayer.PausedState:
            # Если музыка на паузе, продолжаем воспроизведение
            self.player.play()
        else:
            # Воспроизводим музыку с начала
            current_item = self.main_screen.listWidget.currentItem()
            if current_item:
                audio_file = current_item.text()
                path = self.load_path_music_to_delete_and_play(audio_file)
                if not os.path.exists(path):
            # Если трек был удалён, очищаем лейбл и не воспроизводим
                    self.main_screen.label.clear()
                    return
                url = QtCore.QUrl.fromLocalFile(path)
                content = QMediaContent(url)
                self.player.setMedia(content)
                self.player.play()
                self.main_screen.label.setText(f"Сейчас играет: {audio_file}")

    def pauseAudio(self):
        # Если музыка воспроизводится, ставим на паузу
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            # Если музыка на паузе, ничего не делаем
            pass


    def update_slider(self, position):
        self.main_screen.horizontalSlider.setValue(position)

    def update_duration(self, duration):
        self.main_screen.horizontalSlider.setRange(0, duration)

    def set_position(self, position):
        self.player.setPosition(position)

    def load_music_from_db(self):
        conn = self.connectt()
        cur = conn.cursor()
        cur.execute("SELECT title, file_path FROM music")
        rows = cur.fetchall()
            
        for row in rows:
            title, _ = row
            self.main_screen.listWidget.addItem(title)
            
        cur.close()
        conn.close()

    def load_path_music_to_delete_and_play(self, title):
        conn = self.connectt()
        cur = conn.cursor()
        cur.execute("SELECT file_path FROM music WHERE title = %s;",(title,))
        rows = cur.fetchone()
        cur.close()
        conn.close()
        return rows[0]


    def add_music_from_db(self, title, artist, album, file):
        conn = self.connectt()
        cur = conn.cursor()
        cur.execute(
                "INSERT INTO music (title, artist, album, file_path) VALUES (%s, %s, %s, %s)",
                (title, artist, album, file)
                )
        conn.commit()
        cur.close()
        conn.close()



    def remove_music_from_db(self, file_path):
            conn = self.connectt()
            cur = conn.cursor()
            cur.execute("DELETE FROM music WHERE file_path = %s", (file_path,))
            conn.commit()
            cur.close()
            conn.close()




    def connectt(self):
        # Подключение к существующей базе данных
        connection = psycopg2.connect(user="postgres", 
                                            password="123456789", 
                                            host="localhost", 
                                            port="5432", 
                                            database="musicdb",
                                            options="-c search_path=musicschema,public")
        connection.autocommit = True
        return connection
    


    def media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.play_next_audio()

    def play_next_audio(self):
        current_row = self.main_screen.listWidget.currentRow()
        next_row = current_row + 1
        if next_row < self.main_screen.listWidget.count():
            self.main_screen.listWidget.setCurrentRow(next_row)
            self.playAudio()
        else:
            #self.player.stop()
            self.main_screen.listWidget.setCurrentRow(0)
            self.playAudio()


def application():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    application()
