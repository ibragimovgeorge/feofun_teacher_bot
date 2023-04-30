#!/bin/bash
apt update
apt install git
git clone https://github.com/ibragimovgeorge/feofun_teacher_bot
apt install python3
source /venv/bin/activate
pip install -r requirements.txt
deactivate
read -sp 'bot_token: ' bot_token
echo "bot_token =" $bot_token > .env
read -p 'my_father_id: ' my_father_id
echo "my_father_id =" $my_father_id > .env
read -p 'my_mother_id: ' my_mother_id
echo "my_mother_id =" $my_mother_id > .env
read -p 'db_host: ' db_host
echo "db_host =" $db_host > .env
read -p 'db_user: ' db_user
echo "db_user =" $db_user > .env
read -p 'db_password: ' db_password
echo "db_password =" $db_password > .env
read -p 'db_name: ' db_name
echo "db_name =" $db_name > .env
read -p 'monuments_csv_url: ' monuments_csv_url
echo "monuments_csv_url =" $monuments_csv_url > .env
read -p 'restoring _db_file: ' db_dile
sudo apt install postgresql postgresql-contrib
sudo -i -u postgres
createuser $db_user
psql $db_name < $db_file;
ALTER USER $db_user WITH PASSWORD '$db_password';
ALTER TABLE $db_name TO $db_user;
\q
logout
[Unit]
echo "Description=Feofunbot
After=default.target

[Service]
Restart=on-failure
User=$USER
ExecStart=$PWD/venv/bin/python3 $PWD/main.py

[Install]
WantedBy=default.target" > feofun.service
systemctl enable feofun.service
echo "Теперь зайдите в бота и подайте ему команду /update_questions_from_csv, чтобы он обновил БД с вопросами и получил все id картинок от телеграма"
