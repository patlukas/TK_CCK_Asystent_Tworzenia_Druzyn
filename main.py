import csv
import json
import os
import sys
import time
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QWidget,
    QGroupBox,
    QGridLayout,
    QLabel,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QPushButton,
    QMessageBox
)
from PyQt5 import QtCore
from PyQt5 import QtGui


APP_NAME = "ATD"
APP_VERSION = "1.12.0"


class GUI(QDialog):
    def __init__(self):
        super().__init__()
        self.__init_window()
        self.__layout = QHBoxLayout()
        self.setLayout(self.__layout)

        config, list_missing_file, list_missing_dir, bad_path_file = self.__check_all_file_and_dir_exists()
        if len(list_missing_dir) or len(list_missing_file) or len(bad_path_file) or config is False:
            self.__set_layout_missing_file(list_missing_file, list_missing_dir, bad_path_file)
        else:
            self.__config = config
            self.__list_game_type = config["Rodzaje"]
            self.__list_name_game_type = self.__get_list_name_game_type()
            self.__selected_game_type = self.__get_last_selected_game_type()
            self.__get_player_with_valid_licenses = self.__config["valid_licenses"]
            self.__save_with_polish_signs = self.__config["polish_characters"]
            self.__player_section = None
            self.__set_layout()

    def __init_window(self):
        self.setWindowTitle("ATD - Asystent Tworzenia Drużyn")
        self.setWindowIcon(QtGui.QIcon('icon/icon.ico'))
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)
        self.move(300, 50)
        self.layout()

    def __set_layout(self):
        game_type_selection = GameTypeSelection(self.__save_with_polish_signs, self.__get_player_with_valid_licenses,
                                                self.__selected_game_type["name"],
                                                self.__list_name_game_type, self.__on_selected_game_type,
                                                self.__click_checkbox_valid_licenses, self.__click_checkbox_polish_sign)

        self.__player_section = PlayerSection(self.__config,  self.__selected_game_type,
                                              self.__get_player_with_valid_licenses)

        button_save = QPushButton("Stwórz schamaty")
        button_save.clicked.connect(self.__create_schemes)

        author = QLabel("   12.01.2026 patlukas v" + APP_VERSION)
        author.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        license_modify_time = QLabel(self.__get_date_creating_license_file())
        license_modify_time.setAlignment(QtCore.Qt.AlignLeft)

        column1 = QWidget()
        column1_layout = QGridLayout()
        column1.setLayout(column1_layout)

        row1 = QWidget()
        row1_layout = QGridLayout()
        row1.setLayout(row1_layout)

        row1_layout.addWidget(QLabel(""), 0, 0)
        row1_layout.addWidget(game_type_selection, 0, 1)
        row1_layout.addWidget(QLabel(""), 0, 2)

        row4 = QWidget()
        row4_layout = QGridLayout()
        row4.setLayout(row4_layout)
        row4.setContentsMargins(0, 10, 0, 0)

        row4_layout.addWidget(license_modify_time, 0, 0)
        row4_layout.addWidget(author, 0, 1)

        column1_layout.addWidget(row1, 0, 0)

        column1_layout.addWidget(self.__player_section, 1, 0)
        column1_layout.addWidget(button_save, 2, 0)
        column1_layout.addWidget(row4, 3, 0)
        column1_layout.setContentsMargins(10, 10, 10, 0)
        self.__layout.addWidget(column1)
        self.__layout.setContentsMargins(10, 10, 10, 3)

    def __set_layout_missing_file(self, list_missing_file, list_missing_dir, bad_path_file):
        text = ""
        if len(list_missing_file):
            text = "Brakuje następujących plików:"
            for name_file in list_missing_file:
                text += "\n    -   " + name_file
            if len(list_missing_dir) or len(bad_path_file):
                text += "\n\n"

        if len(list_missing_dir):
            text += "Błędna ścieżka do następujących katalogów:"
            for name_file in list_missing_dir:
                text += "\n    -   " + name_file
            if len(bad_path_file):
                text += "\n\n"

        if len(bad_path_file):
            text += "Ścieżki do tych plików nie mogą zawierać \n" \
                    "pojedyńczego '\\', zasmiast tego musi mieć '/' lub '\\\\':"
            for name_file in bad_path_file:
                text += "\n    -   " + name_file
        label = QLabel(text)
        label.setStyleSheet(''' font-size: 24px; color: red''')
        self.__layout.addWidget(label)

    def __check_all_file_and_dir_exists(self):
        """
        Metoda sprawdza czy istnieją obowiązkowe nazwy plików (config.json, cash.json) oraz czy w config.json przy
        podaniu nazwy nie został użyty błędnie '\', poznieważ jest to znak specjalny i aby python go odczytał
        jako '\' trzeba zapisać '\\'
        :return: zawartość config.json <dict>, listę nieznaleznionych plików, listę nieznalezionych katalogów,
                listę błędnie zapisanych nazw plików/katalogów
        """
        list_file_path = ["config.json", "cash.json"]
        list_missing_file, list_missing_dir, bad_path_file = [], [], []
        for file_path in list_file_path:
            if not Path(file_path).is_file():
                list_missing_file.append(file_path)

        if len(list_missing_file) or len(list_missing_dir):
            return False, list_missing_file, list_missing_dir, bad_path_file

        config = self.__get_config()

        if config is False:
            bad_path_file.append("W config.json jest pojedyńczy '\\' zamiast '\\\\'")
            return config, list_missing_file, list_missing_dir, bad_path_file

        file_path = config["license_file"]["path"]
        if self.__check_str_have_backslash(file_path):
            bad_path_file.append(file_path)
        elif not Path(file_path).is_file():
            list_missing_file.append(file_path)

        dir_path = config["path_to_dir_witch_schemes"]
        if self.__check_str_have_backslash(dir_path):
            bad_path_file.append(dir_path)
        elif not Path(dir_path).is_dir():
            list_missing_dir.append(dir_path)

        return config, list_missing_file, list_missing_dir, bad_path_file

    @staticmethod
    def __check_str_have_backslash(string: str) -> bool:
        """Czy str zawiera znaki specjalne"""
        if "\t" in string or "\n" in string or "\r" in string:
            return True
        return False

    def __get_date_creating_license_file(self):
        """Zwraca kiedy ostatno był modyfikowany plik z licencjami."""
        path_to_license_file = self.__config["license_file"]["path"]
        modification_time = time.strftime('%d.%m.%Y', time.localtime(os.path.getmtime(path_to_license_file)))
        return "Licencje: stan na " + modification_time

    @staticmethod
    def __get_config():
        try:
            config = json.load(open("config.json", encoding='utf-8-sig'))
        except ValueError:
            return False
        except AttributeError:
            return False
        return config

    def __get_list_name_game_type(self):
        """Zwraca listę możliwych do wyboru typów gier."""
        list_name = []
        for game_type in self.__list_game_type:
            list_name.append(game_type["name"])
        return list_name

    def __on_selected_game_type(self, new_name_game_type: str):
        """
        Po wyborze w combobox nowego typu gry, jest wyszukiwany obiekt o takiej nazwie i zapisywany w
        self.__selected_game_type oraz jest uruchamiana metoda, która aktualizuje dostępnych graczy do wyboru.
        """
        for game_type in self.__list_game_type:
            if game_type["name"] == new_name_game_type:
                self.__selected_game_type = game_type
        self.__player_section.change_game_type(self.__selected_game_type)

    def __click_checkbox_polish_sign(self, boolean: bool):
        self.__save_with_polish_signs = boolean

    def __click_checkbox_valid_licenses(self, boolean: bool):
        self.__get_player_with_valid_licenses = boolean
        self.__player_section.change_player_with_valid_licenses(boolean)

    def __create_schemes(self):
        path_to_dir = self.__config["path_to_dir_witch_schemes"]
        next_nr, list_file_to_del, list_schemes_name = self.__read_existing_schemes(path_to_dir)
        self.__del_list_file(path_to_dir, list_file_to_del)
        list_schema_names = self.__save_new_schemes(path_to_dir, next_nr, list_schemes_name)
        self.__save_last_game_type(self.__selected_game_type["name"])
        self.__show_message_box_about_schemes_is_ready(list_schema_names)

    @staticmethod
    def __show_message_box_about_schemes_is_ready(list_schema_names):
        msg = QMessageBox()
        msg.setWindowTitle("Info")
        info = "Schematy zostały zapisany. Nazwy zapisanych schematów to:\n"
        for schema_name in list_schema_names:
            info += schema_name + "\n"
        msg.setText(info)
        msg.setIcon(QMessageBox.Information)
        msg.exec_()

    def __read_existing_schemes(self, path_to_dir_witch_schemes: str):
        """
        :return: list[numer kolejnego schematu, lista nazw schamatów do usunięcia, lista nazw schematów]
        """
        next_nr, list_file_to_del, list_schemes_name = 0, [], []
        list_file_name = self.__get_list_file_name_from_path(path_to_dir_witch_schemes)
        for file_name in list_file_name:
            with open(path_to_dir_witch_schemes + "/" + file_name, "r") as file:
                file_content = file.read()
                if "LV-Nr=0" in file_content:
                    list_file_to_del.append(file_name)
                else:
                    list_schemes_name.append(file_content.split("\n", 2)[1].split("=")[1])
                    next_nr = int(file_name.split("ms")[1].split(".ini")[0]) + 1
                file.close()
        return [next_nr, list_file_to_del, list_schemes_name]

    @staticmethod
    def __get_list_file_name_from_path(path: str) -> list:
        """
        Funkcja zwraca posortowaną listę nazw plików z rozszerzeniem ".ini".

        Funckja przegląda folder z ścieżki self.__path oraz wybiera z niego wszystkie pliki kończące się na
        ".ini", następnie sortuje listę znalezionych nazw plików i ją zwraca
        :return: (list<str>) lista nazw plików
        """
        try:
            files = os.listdir(path)
            files = [file for file in files if file.endswith(".ini")]
            files.sort()
            return files
        except FileNotFoundError:
            return []

    @staticmethod
    def __del_list_file(path_to_dir: str, list_name_file):
        for name_file in list_name_file:
            os.remove(path_to_dir + "/" + name_file)

    def __save_new_schemes(self, path_to_dir: str, next_file_nr: int, list_exist_schemes_name):
        list_schema_names = []
        schemes_data = self.__player_section.get_data()
        how_many_players_in_scheme = len(self.__selected_game_type["order_of_player"])
        for i, scheme_data in enumerate(schemes_data):
            name = self.__get_unique_schema_name(list_exist_schemes_name, scheme_data["name"])
            if self.__selected_game_type["type"] == "turniej":
                self.__save_name_tournament(name)
            list_exist_schemes_name.append(name)
            list_schema_names.append(name)
            file_text = "[Allgemein]\nName=" + str(name) + "\nSpielklasse=\nLiga=\nBezirk=\nSpielführer=\nBetreuer " \
                        "1=\nVereins-Nr=\nLV-Nr=0\nAnzahl Spieler=" + str(len(scheme_data["players"])) + "\n"
            nr_player = 0
            index_order = 0
            while nr_player < len(scheme_data["players"]) or index_order % how_many_players_in_scheme != 0:
                order_of_player = self.__selected_game_type["order_of_player"][index_order%how_many_players_in_scheme]
                last_name, name, team = "Player", "No", ""
                if order_of_player == 1:
                    player_data = scheme_data["players"][nr_player]
                    nr_player += 1
                    last_name, name, team = player_data['last_name'], player_data['name'], player_data['team']
                    last_name = self.__standardization_to_windows_restriction(last_name)
                    name = self.__standardization_to_windows_restriction(name)
                    team = self.__standardization_to_windows_restriction(team, True)
                file_text += "[Spieler " + str(index_order) + "]\nName=" + str(name) + "\nVorname=" + str(last_name) + \
                             "\nLetztes Spiel=\nPlatz-Ziffer=\n Spielernr.=\nGeb.-Jahr=\nAltersklasse=\nPass-Nr.=\n" \
                             "Rangliste=\nVerein=" + str(team) + "\n"
                index_order += 1
            if self.__save_with_polish_signs is False:
                file_text = self.__remove_polish_characters(file_text)
            file = open(str(path_to_dir) + "/ms" + str(next_file_nr + i) + ".ini", "w")
            file.write(file_text)
            file.close()
        return list_schema_names

    @staticmethod
    def __standardization_to_windows_restriction(name: str, can_empty=False) -> str:
        """
        Metoda standaryzuje przekazaną nazwę, aby mogła być wykorzystana jako nazwa pliku/katalogu w Windowsie,
        czyli usuwa '.' na początku i końcu, usuwa spacje na początku i końcu i usuwa znaki specjalne
        :param name: wpisana przez użytkowaika nazwa
        :param can_empty: czy może zostać zwrócony pusty string
        :return: ustandaryzowany string
        """
        name = name.strip()
        list_replace = ["/", "\\", ":", "*", "?", "\"", "<", ">", "|"]
        for old in list_replace:
            name = name.replace(old, "")
        if len(name) and name[0] == ".":
            name = name[1:]
        if len(name) and name[-1] == ".":
            name = name[:-1]
        if name == "" and not can_empty:
            return "_"
        return name

    def __get_unique_schema_name(self, list_exist_schemes_name, name: str) -> str:
        """
        Metoda zwraca unikalną nazwę schematu. Jeżeli gracz chciał bez poliskich znaków, taka zostanie zwrócona.
        :param list_exist_schemes_name: lista już użytych nazw schematów
        :param name: wpisana przez użytkowaika nazwa schematu
        :return: unikalna nazwa schematu, która jeżeli użytkownik tak chciał nie ma polskich znaków
        """
        name = self.__standardization_to_windows_restriction(name)
        if self.__save_with_polish_signs is False:
            name = self.__remove_polish_characters(name)
        while name in list_exist_schemes_name:
            name += "_"
        return name

    @staticmethod
    def __remove_polish_characters(text: str) -> str:
        list_replace = [
            ["Ą", "A"], ["Ę", "E"], ["Ć", "C"], ["Ł", "L"], ["Ń", "N"], ["Ż", "Z"], ["Ź", "Z"], ["Ó", "O"], ["Ś", "S"],
            ["ą", "a"], ["ć", "c"], ["ę", "e"], ["ł", "l"], ["ń", "n"], ["ó", "o"], ["ś", "s"], ["ź", "z"], ["ż", "z"]
        ]
        for old, new in list_replace:
            text = text.replace(old, new)
        return text

    @staticmethod
    def __save_name_tournament(name: str):
        filename = 'cash.json'
        with open(filename, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
            data['tournament_name'] = name

        os.remove(filename)
        with open(filename, 'w', encoding='utf-8-sig') as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def __save_last_game_type(name_game_type: str):
        filename = 'cash.json'
        with open(filename, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
            data['last_game_type'] = name_game_type

        os.remove(filename)
        with open(filename, 'w', encoding='utf-8-sig') as f:
            json.dump(data, f, indent=4)

    def __get_last_selected_game_type(self) -> dict:
        cash = json.load(open("cash.json", encoding='utf-8-sig'))
        game_type_name = cash["last_game_type"]
        for game_type in self.__list_game_type:
            if game_type["name"] == game_type_name:
                return game_type
        return self.__list_game_type[0]


class GameTypeSelection(QGroupBox):
    def __init__(self, default_bool_polish_characters: bool, default_bool_valid_licenses: bool,
                 name_selected_game_type: str, list_name_game_type, on_selected_game_type,
                 click_checkbox_valid_licenses, click_checkbox_polish_sign):
        super().__init__("Główne ustawienia")
        self.__on_selected_game_type = on_selected_game_type
        self.__click_checkbox_polish_sign = click_checkbox_polish_sign
        self.__click_checkbox_valid_licenses = click_checkbox_valid_licenses
        self.__list_name_game_type = list_name_game_type
        self.__layout = QGridLayout()
        self.__label_types = None
        self.__combobox_game_type = None
        self.__checkbox_valid_licenses = None
        self.__checkbox_with_polish_signs = None
        self.__create_widgets(default_bool_valid_licenses, default_bool_polish_characters, name_selected_game_type)
        self.setLayout(self.__layout)
        self.__set_layout()

    def __create_widgets(self, default_bool_valid_licenses: bool, default_bool_polish_characters: bool,
                         name_selected_game_type: str):
        self.__label_types = QLabel("Rodzaj rozgrywanych zawodów: ")
        self.__combobox_game_type = QComboBox()
        self.__combobox_game_type.addItems(self.__list_name_game_type)
        self.__combobox_game_type.setCurrentText(name_selected_game_type)
        self.__combobox_game_type.currentTextChanged.connect(self.__on_selected_game_type)

        self.__checkbox_valid_licenses = QCheckBox("Wyświetlani gracze muszą mieć ważną licencję")
        self.__checkbox_valid_licenses.setChecked(default_bool_valid_licenses)
        self.__checkbox_valid_licenses.clicked.connect(self.__click_checkbox_valid_licenses)

        self.__checkbox_with_polish_signs = QCheckBox("Tworzony schemat może zawierać polskie znaki")
        self.__checkbox_with_polish_signs.setChecked(default_bool_polish_characters)
        self.__checkbox_with_polish_signs.clicked.connect(self.__click_checkbox_polish_sign)

        self.__checkbox_valid_licenses.setToolTip("Jeżeli opcja jest wybrana, to tylko gracze z ważną licencją będą "
                                                  "pokazani na liście wyboru graczy.")
        self.__checkbox_with_polish_signs.setToolTip("Jeżeli opcja nie zostanie wybrana, to np. zamiast 'Gostyń' "
                                                     "będzie wpisane w schemacie 'Gostyn'")

    def __set_layout(self):
        self.__layout.addWidget(self.__label_types, 0, 0)
        self.__layout.addWidget(self.__combobox_game_type, 0, 1)
        self.__layout.addWidget(self.__checkbox_valid_licenses, 1, 0, 1, 2)
        self.__layout.addWidget(self.__checkbox_with_polish_signs, 2, 0, 1, 2)


class PlayerSection(QWidget):
    def __init__(self, config, game_type: dict, player_with_valid_licenses: bool):
        super().__init__()
        self.__settings_game_type = game_type
        self.__player_with_valid_licenses = player_with_valid_licenses
        self.__widgets = []
        self.__list_team_name = []
        self.__number_of_player_in_team = 0
        self.__list_age_category = []
        self.__license_config = config["license_file"]
        self.__license_file = open(self.__license_config["path"], "r", encoding='utf-8-sig')
        self.__with_loaned = False
        self.__layout = QGridLayout()
        self.setLayout(self.__layout)
        self.set_layout()

    def change_game_type(self, game_type):
        self.__settings_game_type = game_type
        self.set_layout()

    def change_player_with_valid_licenses(self, player_with_valid_licenses: bool):
        self.__player_with_valid_licenses = player_with_valid_licenses
        self.set_layout()

    def set_layout(self):
        for i in reversed(range(self.__layout.count())):
            self.__layout.itemAt(i).widget().deleteLater()
        number_of_team = self.__settings_game_type["number_of_team"]
        self.__number_of_player_in_team = sum(self.__settings_game_type["order_of_player"])
        self.__with_loaned = self.__settings_game_type["with_loaned"]
        self.__list_age_category = self.__settings_game_type["list_age_category"]
        self.__list_team_name = self.__get_list_team()
        self.__widgets = []
        for i in range(number_of_team):
            self.__widgets.append({})
            home, head = False, "Blok"
            if self.__settings_game_type["type"] != "turniej":
                head = "Drużyna nr " + str(i + 1)
                if i == 0:
                    home = True
            self.__layout.addWidget(self.__team_column(head, self.__widgets[i], home), 0, i)

    def __team_column(self, name: str, dict_widgets: dict, home: bool):
        widget = QGroupBox(name)

        combobox_team = QComboBox()
        combobox_team.addItems(self.__list_team_name)
        if home:
            combobox_team.setCurrentText(self.__get_home_team())
        combobox_team.setToolTip("Wybór do której drużyny muszą należeć gracze")

        combobox_number_of_block = QComboBox()
        combobox_number_of_block.addItems([str(i) for i in range(1, 17)])

        input_name_team = QLineEdit()

        layout = QGridLayout()
        widget.setLayout(layout)
        if self.__settings_game_type["type"] != "turniej":
            layout.addWidget(QLabel("Filtr graczy"), 0, 0)
            layout.addWidget(combobox_team, 0, 1)
        layout.addWidget(QLabel("Nazwa schematu"), 1, 0)
        layout.addWidget(input_name_team, 1, 1)

        list_combobox_player = []
        for i in range(self.__number_of_player_in_team):
            combobox_player = QComboBox()
            combobox_player.setEditable(True)
            list_combobox_player.append(combobox_player)
            layout.addWidget(QLabel("Gracz " + str(i + 1)), 2 + i, 0)
            layout.addWidget(combobox_player, 2 + i, 1)

        if self.__settings_game_type["type"] == "turniej":
            layout.addWidget(QLabel("Liczba bloków"), self.__number_of_player_in_team + 3, 0)
            layout.addWidget(combobox_number_of_block, self.__number_of_player_in_team + 3, 1)

        dict_widgets["combobox_team"] = combobox_team
        dict_widgets["combobox_number_of_block"] = combobox_number_of_block
        dict_widgets["input_name_team"] = input_name_team
        dict_widgets["list_combobox_player"] = list_combobox_player

        combobox_team.currentTextChanged.connect(lambda: self.__set_list_player_in_combobox(dict_widgets))
        self.__set_list_player_in_combobox(dict_widgets)
        return widget

    def __set_list_player_in_combobox(self, dict_widgets: dict):
        if self.__settings_game_type["type"] == "turniej":
            dict_widgets["input_name_team"].setText(self.__get_tournament_name())
            name_team = ""
        else:
            name_team = dict_widgets["combobox_team"].currentText()
            dict_widgets["input_name_team"].setText("_ " + name_team + " _")

        list_players = self.__get_list_players(name_team)

        for combobox_player in dict_widgets["list_combobox_player"]:
            combobox_player.clear()
            for player in list_players:
                combobox_player.addItem(player["full_name"], player)

    def __get_list_team(self) -> list:
        index_column_name = self.__license_config["index_column"]["name"]
        index_column_team = self.__license_config["index_column"]["team"]
        index_column_age_category = self.__license_config["index_column"]["age_category"]
        index_column_license_is_valid = self.__license_config["index_column"]["license_is_valid"]
        index_column_where_loaned = self.__license_config["index_column"]["where_loaned"]
        list_team = [""]

        csv_reader = csv.reader(self.__license_file)
        self.__license_file.seek(0)
        line_count = 0
        for row in csv_reader:
            if line_count > 0:
                if len(self.__list_age_category) > 0 and row[index_column_age_category] not in self.__list_age_category:
                    continue
                if self.__player_with_valid_licenses is True and row[index_column_license_is_valid] != "TAK":
                    continue
                last_name_and_name = row[index_column_name].split(" ", 1)
                if len(last_name_and_name) != 2:
                    continue
                team = row[index_column_team]
                if self.__with_loaned and row[index_column_where_loaned] != "":
                    team = row[index_column_where_loaned]
                team = team.strip()
                if team not in list_team:
                    list_team.append(team)
            line_count += 1
        list_team.sort()
        return list_team

    def __get_list_players(self, team: str) -> list:
        index_column_name = self.__license_config["index_column"]["name"]
        index_column_team = self.__license_config["index_column"]["team"]
        index_column_age_category = self.__license_config["index_column"]["age_category"]
        index_column_license_is_valid = self.__license_config["index_column"]["license_is_valid"]
        index_column_where_loaned = self.__license_config["index_column"]["where_loaned"]
        list_licenses = [{
            "full_name": "",
            "team": "",
            "last_name": "No",
            "name": "Player"
        }]

        self.__license_file.seek(0)
        csv_reader = csv.reader(self.__license_file)
        line_count = 0
        for row in csv_reader:
            if line_count > 0:
                player_team = ""
                if len(self.__list_age_category) > 0 and row[index_column_age_category] not in self.__list_age_category:
                    continue
                if self.__with_loaned and row[index_column_where_loaned] != "":
                    player_team = row[index_column_where_loaned]
                else:
                    player_team = row[index_column_team]
                player_team = player_team.strip()
                if team != "" and player_team != team:
                    continue
                if self.__player_with_valid_licenses is True and row[index_column_license_is_valid] != "TAK":
                    continue
                full_name = row[index_column_name].strip()
                last_name_and_name = full_name.split(" ", 1)
                if len(last_name_and_name) != 2:
                    continue
                list_licenses.append({
                    "full_name": full_name,
                    "team": player_team,
                    "last_name": last_name_and_name[0].strip(),
                    "name": last_name_and_name[1].strip()
                })
            line_count += 1

        list_licenses = sorted(list_licenses, key=lambda x: x['full_name'])

        return list_licenses

    def get_data(self):
        data = []
        for widget in self.__widgets:
            list_players = []
            for player_combobox in widget["list_combobox_player"]:
                current_text = player_combobox.currentText()
                current_data = player_combobox.currentData()
                if current_text == current_data["full_name"]:
                    list_players.append({
                        "name": current_data["name"],
                        "last_name": current_data["last_name"],
                        "team": current_data["team"]
                    })
                else:
                    names = current_text.split(" ")
                    if len(names) == 1:
                        names.append("No")
                    list_players.append({
                        "name": names[1],
                        "last_name": names[0],
                        "team": ""
                    })

            number_additional_block = int(widget["combobox_number_of_block"].currentText())-1
            for i in range(number_additional_block):
                for j in range(self.__number_of_player_in_team):
                    list_players.append({
                        "name": "Blok_" + str(i + 2),
                        "last_name": "Tor_" + str(j + 1),
                        "team": ""
                    })

            data.append({
                "name": widget["input_name_team"].text(),
                "players": list_players
            })
        return data

    @staticmethod
    def __get_tournament_name() -> str:
        f = open("cash.json", encoding='utf-8-sig')
        cash = json.load(f)
        return cash["tournament_name"]

    @staticmethod
    def __get_home_team() -> str:
        f = open("cash.json", encoding='utf-8-sig')
        cash = json.load(f)
        return cash["home_team"]


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = GUI()
    ex.show()
    sys.exit(app.exec_())
