
# interview-project
Small project to test candidates with their debugging and coding skills
=======
# Interview Project
Small project to test debugging and coding skills. In this project you are required to deploy a simple
application then investigate and resolve a few issues that have been inserted for the purpose of this
exercise. Once these issues have been resolved and the basic application is working, you will write
an additional application to feed additional data.


## Deployment

Chose a Kubernetes environment of your choice and deploy the manifest included as part of this
project.

	kubectl apply -f manifest.yaml


## Expected Results

Once the application has been deployed and issues resolved, you should be able to port forward to the
`webapp` on port 5000.

	kubectl port-forward service/webapp 5000

Then from your browser navigate to `http://localhost:5000`. If everything is working as expected you
will see:

![](https://storage.googleapis.com/arize-assets/doc-images/interview-project/expected.png)

# Enhancements

With the application working, your task is to create a new application and add it to the existing
manifest. The new application should populate the database with periodic data. For example injecting
current temperature or stock information every hour.


