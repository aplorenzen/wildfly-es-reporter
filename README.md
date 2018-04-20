# wildfly-es-reporter
This is a python script that will retrieve statistics from a Wildfly instance and report them to an elasticsearch instance.

docker run -p 5601:5601 -p 9200:9200 -p 5044:5044 -it --name elk sebp/elk