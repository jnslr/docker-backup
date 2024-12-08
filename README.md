# Docker-backup

## Development

Development can be done in a docker container itself:
Create a container with 
`docker container run --name docker-backup-dev -d -it -p 8124:80 -v /var/run/docker.sock:/var/run/docker.sock -v .:/home/git/docker-backup -w /home/git/docker-backup ghcr.io/jnslr/docker-backup:main /bin/sh`


Then connect via VsCode and install the Vscode debug extension as well

`docker container stop docker-backup-dev`
`docker container rm -f docker-backup-dev`