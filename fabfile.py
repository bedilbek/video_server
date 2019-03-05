from fabric import Connection, task

@task
def deploy(c):
    connection = Connection('52.191.135.20', 'bedilbek', 22)
    with connection.cd('/home/bedilbek/attention_server'):
        connection.run('sudo kill $(sudo lsof -t -i:8080)')
        connection.run('rm -rf venv/')
        connection.run('git reset --hard')
        connection.run('git pull origin master')
        connection.run('python3.6 -m virtualenv venv')
        with connection.prefix('source venv/bin/activate'):
            connection.run('pip install -r requirements.txt')
            connection.run('nohup python server.py &')
            connection.run("echo 'server is running'")
    print('server restarted, everything is ok')
