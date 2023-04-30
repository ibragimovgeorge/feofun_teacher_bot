#!/bin/bash
apt update
apt install git
git clone https://github.com/ibragimovgeorge/feofun_teacher_bot
apt install python3
cd $PWD/feofun_teacher_bot
sudo apt install python3-venv
python3 -m venv feofun_venv
source $PWD/feofun_venv/bin/activate
pip install -r requirements.txt
deactivate
read -sp 'bot_token: ' bot_token
echo "bot_token =" $bot_token > .env
echo -e "\n"
read -p 'my_father_id: ' my_father_id
echo "my_father_id =" $my_father_id >> .env
read -p 'my_mother_id: ' my_mother_id
echo "my_mother_id =" $my_mother_id >> .env
read -p 'db_host: ' db_host
echo "db_host =" $db_host >> .env
read -p 'db_user: ' db_user
echo "db_user =" $db_user >> .env
read -p 'db_password: ' db_password
echo "db_password =" $db_password >> .env
read -p 'db_name: ' db_name
echo "db_name =" $db_name >> .env
read -sp 'monuments_csv_url: ' monuments_csv_url
echo "monuments_csv_url =" $monuments_csv_url >> .env
echo -e "\n"
read -p 'restoring _db_file: ' db_file
sudo apt install postgresql postgresql-contrib
sudo -u postgres createuser $db_user
sudo -u postgres createdb -O $db_user $db_name
cd ..
sudo -u postgres psql -c "alter role $db_user with password '$db_password'"
sudo -u postgres psql $db_name < $db_file

echo "[Unit]
Description=Feofunbot
After=default.target

[Service]
Restart=on-failure
User=$USER
ExecStart=$PWD/feofun_teacher_bot/feofun_venv/bin/python3 $PWD/feofun_teacher_bot/main.py

[Install]
WantedBy=default.target" > $PWD/feofun.service
systemctl enable $PWD/feofun.service
systemctl start feofun
echo "Теперь зайдите в бота и подайте ему команду /update_questions_from_csv, чтобы он обновил БД с вопросами и получил все id картинок от телеграма"
